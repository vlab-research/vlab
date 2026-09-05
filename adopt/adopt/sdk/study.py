"""A vlab study as a file on disk: load, save, diff, and the order to write in.

Pure. Nothing here opens a socket; `client.py` does that, and the CLI wires the
two together. The split is what lets a notebook build strata however it likes
(plan §6.D) and still get the file handling, the diff and the push ordering for
free.

THE FILE
--------

One document, `study.yaml` (or `.json` -- YAML 1.1 parses JSON, so the loader
does not care and only the writer does). Flat: a three-key header, then the
nine configuration sections under their names AS STORED::

    org:  0f1e...              # the org UUID. Must be handed to you (§7.1).
    slug: hpv-nigeria          # from the 201 of `vlab create`
    name: HPV Nigeria          # informational; the server owns the real one

    general:        {...}
    recruitment:    {...}
    destinations:   [...]
    ...

The section VALUES are the wire shapes verbatim -- exactly what
`POST /confs/<type>` takes and exactly what `GET /confs` gives back. No
translation layer, deliberately: the moment the file has its own schema, the
SDK owns a second definition of what a study is, which is the failure that made
the dashboard's TypeScript compiler a problem in the first place (plan §4).
`documentation/agent-api.md` §3 is therefore the file format's documentation
too, and stays correct for free.

Keys are the STORED names -- `data_sources` and `inference_data`, with
underscores -- not the hyphenated URL segments you POST to. That is what
`GET /confs` hands back and what `validate_study` takes, so a
read-modify-validate-write loop needs no renaming anywhere; the one place the
hyphens exist is `SECTION_URL_SEGMENTS`, used only when building the POST path.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import yaml
from pydantic import TypeAdapter

from ..authoring.validate import SECTION_MODELS

# The nine, in the order they are written to a file. Canonical rather than
# alphabetical: it is the order of `documentation/agent-api.md` §3 and of the
# dashboard's own tabs, so a file reads top to bottom the way the docs do.
SECTIONS: Tuple[str, ...] = (
    "general",
    "recruitment",
    "destinations",
    "creatives",
    "audiences",
    "variables",
    "strata",
    "data_sources",
    "inference_data",
)

# Stored conf type -> the URL segment that writes it. Two of the nine differ,
# and the mismatch is a real trap: you POST to `confs/data-sources` and the row
# is stored as `data_sources` (`server/server.py`).
SECTION_URL_SEGMENTS: Dict[str, str] = {
    name: name.replace("_", "-") for name in SECTIONS
}

# The order `push` writes in. The server checks NOTHING across sections, so
# this order buys the server nothing; it is for the human and the agent reading
# the output, and for the failure case. A push can stop half way -- a 422 on
# creatives leaves destinations already written -- and this ordering means what
# is on the server at that moment is always a prefix of the reference graph
# rather than a middle of it: a stratum is never stored naming a creative that
# was not written, a creative never names a destination that was not.
#
# `recruitment` is last for a different and sharper reason: its
# `start_date`/`end_date` window is the study's on/off switch, and the
# `study_state` view is what makes a study visible to the crons at all
# (`agent-api.md` §3). Writing it last means the two-hourly `adopt-ads` run
# cannot pick the study up half-configured. Runbook step 9 says the same thing.
PUSH_ORDER: Tuple[str, ...] = (
    "general",
    "destinations",
    "creatives",
    "audiences",
    "variables",
    "strata",
    "data_sources",
    "inference_data",
    "recruitment",
)

HEADER_KEYS: Tuple[str, ...] = ("org", "slug", "name")

_ADAPTERS = {name: TypeAdapter(model) for name, model in SECTION_MODELS.items()}


# ---------------------------------------------------------------------------
# The union tags, and why normalisation has to know about them
# ---------------------------------------------------------------------------


def infer_recruitment_type(body: Mapping[str, Any]) -> Optional[str]:
    """The `type` tag a recruitment conf would be given if it carried none.

    Prefers `study_conf._infer_recruitment_type` when it exists, so that once
    PR #262 lands there is one definition rather than two. The fallback
    reproduces it exactly, INCLUDING the test order, which is load-bearing:
    `ad_campaign_name` then `arms` then `destinations` is what pydantic's
    untagged union already resolves to today, and a body carrying both `arms`
    and `destinations` therefore reads as pipeline in both places. Getting that
    order wrong would make `vlab diff` claim a study's recruitment strategy had
    changed when nothing had.

    `None` means "not inferable" -- an empty body, or one with none of the
    three discriminating keys. An explicit tag is returned as-is: only a
    missing or empty one is inferred, matching the narrowness of the real
    validator.
    """
    if not isinstance(body, dict):
        return None

    try:
        from ..study_conf import _infer_recruitment_type  # type: ignore[attr-defined]
    except ImportError:
        pass
    else:
        result = _infer_recruitment_type(dict(body))
        return result.get("type") if isinstance(result, dict) else None

    if body.get("type"):
        return body["type"]
    if "ad_campaign_name" in body:
        return "simple"
    if "arms" in body:
        return "pipeline_experiment"
    if "destinations" in body:
        return "destination"
    return None


# A destination with no `type` is defaulted to `messenger`
# (`study_conf._default_missing_destination_type`), for the 45 stored confs
# that predate the field. There is no shape inference here and there must not
# be: shape-matching destinations is exactly what silently turned every `multi`
# destination into a `messenger` one and got a live study's ads rejected on
# 2026-08-30.
DESTINATION_DEFAULT_TYPE = "messenger"


def _strip_inferred_tag(section: str, value: Any) -> Any:
    """Drop a `type` key that carries no information beyond the body's shape.

    The problem this solves is version skew, in both directions. A server
    running PR #262 or later stores a `type` on every recruitment conf, because
    `model_dump()` now emits one; a server older than it drops the tag on the
    way in, because `extra="ignore"` ate it. Either way an SDK writing the tag
    (which it should -- new configuration ought to be explicit) would otherwise
    see a permanent, unfixable difference between the file and the store, and
    `vlab push` would re-POST the same section forever, appending a row to an
    append-only table each time.

    So: a `type` equal to what the body would have been tagged with anyway is
    not a difference. A `type` that DISAGREES with the shape is kept here --
    though against a server older than #262 it is then dropped by
    `model_dump_section` anyway, because the model does not declare the field
    at all. That is the honest answer for that server (it would drop the tag
    too, so pushing changes nothing), and the disagreement still surfaces:
    `unknown_keys` exempts only a tag that restates the shape, so a
    contradicting one is reported as an undeclared key. From #262 onwards the
    same body is a 422 from the discriminated union.
    """
    if section == "recruitment" and isinstance(value, dict) and "type" in value:
        without = {k: v for k, v in value.items() if k != "type"}
        if value["type"] == infer_recruitment_type(without):
            return without
        return value

    if section == "destinations" and isinstance(value, list):
        return [
            {k: v for k, v in item.items() if k != "type"}
            if isinstance(item, dict) and item.get("type") == DESTINATION_DEFAULT_TYPE
            else item
            for item in value
        ]

    return value


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------


def model_dump_section(section: str, value: Any) -> Optional[Any]:
    """`value` as the server would store it, or `None` if it does not parse.

    `create_conf` stores `config.model_dump()`, not the request body, so the
    stored conf differs from what was sent in two ways every time: unknown keys
    are gone and defaults are filled in (`agent-api.md` §2.1). Diffing a file
    against a stored conf without reproducing that would report a change on
    every section whose file omits an optional field -- which is most of them.

    `mode="json"` because the stored value went through `orjson.dumps`, so
    dates and datetimes come back as ISO strings. `mode="python"` would leave
    them as `datetime` objects and every recruitment conf would diff against
    itself.

    The LENIENT models, not PR #262's strict twins: what a diff is asking is
    "does the store hold what my file says", and the store is read by
    `StudyConf` on the run path. `unknown_keys` covers the write-side
    strictness separately, where it belongs.
    """
    adapter = _ADAPTERS.get(section)
    if adapter is None:
        return None
    try:
        return adapter.dump_python(adapter.validate_python(value), mode="json")
    except Exception:  # noqa: BLE001
        # Every failure mode is the same answer: we cannot say what the server
        # would store, so compare raw. `AudienceConf` in particular raises a
        # bare `KeyError` for a missing `subtype` rather than a pydantic error
        # (plan §14.4), so catching `ValidationError` alone would not do.
        return None


def normalise_section(section: str, value: Any) -> Any:
    """The comparable form of a section: server-stored shape, tags stripped."""
    dumped = model_dump_section(section, value)
    return _strip_inferred_tag(section, value if dumped is None else dumped)


def unknown_keys(section: str, value: Any) -> List[str]:
    """Paths in `value` that the section's model does not declare.

    Uses pydantic as the oracle rather than walking model fields: anything
    present in the input and absent from `model_dump()` of the parsed input is,
    by construction, a key the model dropped -- at any depth, through unions,
    through lists.

    Why this is worth reporting at all: every conf model runs on pydantic's
    default `extra="ignore"`, so a misspelled OPTIONAL field is accepted with a
    `201` and silently discarded (plan §11.4 item 2). For a dashboard user the
    form supplies the names and this cannot happen; for an agent authoring JSON
    it is the likeliest failure mode there is. PR #262 turns it into a 422
    naming the key, which is better, but an SDK that reports it locally works
    against both servers and reports it before the write rather than after.

    Deliberately NOT part of `vlab validate`. That command is a wrapper over
    `authoring.validate.validate_study` and must give the same answer as
    `POST /validate`, which uses the same lenient models and would not report
    this. Unknown keys are a fact about the WIRE, so they surface in `diff` and
    `push`, which are the commands about the wire.

    The `type` tags are exempt for the reason `_strip_inferred_tag` gives: on a
    server older than #262 `type` on recruitment really is an undeclared key,
    and reporting it would mean telling every user of the skeleton this SDK
    generates that their file is wrong.
    """
    parsed = model_dump_section(section, value)
    if parsed is None:
        # It did not parse; whatever is wrong with it is not "an extra key",
        # and `validate` will have said so with a better message.
        return []
    return sorted(_missing_paths(value, parsed, section, ""))


def _missing_paths(raw: Any, dumped: Any, section: str, prefix: str) -> List[str]:
    out: List[str] = []

    if isinstance(raw, dict) and isinstance(dumped, dict):
        for key, value in raw.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key not in dumped:
                if _is_exempt_tag(section, prefix, key, raw):
                    continue
                out.append(path)
            else:
                out.extend(_missing_paths(value, dumped[key], section, path))
        return out

    if isinstance(raw, list) and isinstance(dumped, list) and len(raw) == len(dumped):
        for i, (r, d) in enumerate(zip(raw, dumped)):
            out.extend(_missing_paths(r, d, section, f"{prefix}[{i}]"))
        return out

    return out


def _is_exempt_tag(section: str, prefix: str, key: str, raw: Mapping[str, Any]) -> bool:
    if key != "type":
        return False
    if section == "recruitment" and prefix == "":
        without = {k: v for k, v in raw.items() if k != "type"}
        return raw["type"] == infer_recruitment_type(without)
    return False


# ---------------------------------------------------------------------------
# The diff
# ---------------------------------------------------------------------------

# `remote_only` is not "deleted". There is no way to remove a section through
# the API at all: every read takes the newest row per conf type and there is no
# way to write "no such section" (§1.1). So a section on the server that the
# file omits is reported and then left alone; `push` will never touch it.
STATUSES = ("new", "changed", "unchanged", "remote_only")


@dataclass(frozen=True)
class SectionDiff:
    section: str
    status: str
    local: Any = None
    stored: Any = None
    #: Paths in the local section the models do not declare. See `unknown_keys`.
    unknown: Tuple[str, ...] = ()

    @property
    def needs_push(self) -> bool:
        return self.status in ("new", "changed")


def diff_sections(
    local: Mapping[str, Any], stored: Mapping[str, Any]
) -> List[SectionDiff]:
    """Per-section comparison of a study file against what the server holds.

    Ordered by `SECTIONS`, with any unrecognised key in either side last, so
    the output is stable between runs and between studies.
    """
    # The nine in canonical order, then anything else either side carries. A
    # conf type outside the nine is possible -- `study_confs.conf_type` has no
    # constraint -- and reporting it beats pretending it is not there.
    ordered = list(SECTIONS) + sorted((set(local) | set(stored)) - set(SECTIONS))

    out: List[SectionDiff] = []
    for name in ordered:
        has_local = name in local and local[name] is not None
        has_stored = name in stored and stored[name] is not None

        if not has_local and not has_stored:
            continue
        if not has_local:
            out.append(SectionDiff(name, "remote_only", stored=stored[name]))
            continue

        unknown = tuple(unknown_keys(name, local[name]))
        if not has_stored:
            out.append(SectionDiff(name, "new", local=local[name], unknown=unknown))
            continue

        same = normalise_section(name, local[name]) == normalise_section(
            name, stored[name]
        )
        out.append(
            SectionDiff(
                name,
                "unchanged" if same else "changed",
                local=local[name],
                stored=stored[name],
                unknown=unknown,
            )
        )

    return out


def value_diff(stored: Any, local: Any, prefix: str = "") -> List[Tuple[str, Any, Any]]:
    """`(path, stored, local)` for every leaf that differs. `_ABSENT` for missing.

    A section-level "changed" is almost no information: the sections that get
    long are `strata` and `creatives`, and "strata changed" on a study with
    forty strata does not tell you whether a quota moved or every ad set is
    about to be renamed -- and renaming a stratum id DELETES an ad set with its
    learning and history (§1.4). So the diff goes to the leaf.

    Lists are compared positionally rather than matched by key. It is the wrong
    answer for an inserted element (everything after it reads as changed) and
    the right one for the common edit (a value changed in place), and matching
    by `id`/`name` would need a per-section rule and would still be a guess for
    `question_targeting.vars`. The caller shows a bounded number of lines, so a
    noisy positional diff is capped rather than overwhelming.
    """
    out: List[Tuple[str, Any, Any]] = []

    if isinstance(stored, dict) and isinstance(local, dict):
        for key in list(stored) + [k for k in local if k not in stored]:
            path = f"{prefix}.{key}" if prefix else str(key)
            out.extend(
                value_diff(stored.get(key, _ABSENT), local.get(key, _ABSENT), path)
            )
        return out

    if isinstance(stored, list) and isinstance(local, list):
        for i in range(max(len(stored), len(local))):
            path = f"{prefix}[{i}]"
            out.extend(
                value_diff(
                    stored[i] if i < len(stored) else _ABSENT,
                    local[i] if i < len(local) else _ABSENT,
                    path,
                )
            )
        return out

    if stored != local:
        out.append((prefix, stored, local))
    return out


class _Absent:
    """A leaf on one side only. Not `None`, which is a real JSON value here --
    `creatives[].tags` is genuinely null and that is not the same as absent."""

    def __repr__(self) -> str:
        return "(absent)"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, _Absent)

    def __hash__(self) -> int:
        return hash("_Absent")


_ABSENT = _Absent()


def push_plan(diffs: Sequence[SectionDiff]) -> List[SectionDiff]:
    """The subset of `diffs` that needs writing, in `PUSH_ORDER`."""
    by_name = {d.section: d for d in diffs if d.needs_push}
    # A section outside the nine cannot be pushed -- there is no route for it --
    # so nothing else is appended here. It is not silently forgotten either:
    # `validate_study` reports it as `section.unrecognized`, which is how a
    # typo'd section name (which would otherwise do nothing at all) surfaces.
    return [by_name[n] for n in PUSH_ORDER if n in by_name]


# ---------------------------------------------------------------------------
# The file
# ---------------------------------------------------------------------------


@dataclass
class StudyFile:
    org: Optional[str] = None
    slug: Optional[str] = None
    name: Optional[str] = None
    sections: Dict[str, Any] = field(default_factory=dict)
    #: Top-level keys that are neither header nor one of the nine. Kept rather
    #: than dropped, so `save` after `strata generate` does not silently delete
    #: a user's own annotations.
    #:
    #: `all_sections()`, not `sections`, is what goes to the validator: a typo'd
    #: section name would otherwise do NOTHING AT ALL -- not written, not
    #: reported, not missed -- which is the worst outcome available. Passing the
    #: extras through means `validate_study` reports `section.unrecognized`,
    #: which is exactly the code it has for this.
    extra: Dict[str, Any] = field(default_factory=dict)
    path: Optional[str] = None

    # -- reading -----------------------------------------------------------

    @classmethod
    def loads(cls, text: str, path: Optional[str] = None) -> "StudyFile":
        # `safe_load`, never `load`: a study file may well arrive from an agent
        # or a shared repository, and `yaml.load` constructs arbitrary Python
        # objects. It also parses JSON, so one loader covers both formats.
        try:
            raw = yaml.safe_load(text)
        except yaml.YAMLError as e:
            # Re-raised as a ValueError so the CLI's error handling catches it:
            # a typo in the user's YAML is the user's input being wrong, not a
            # defect in the SDK, and it must not print a traceback. The parser's
            # own message carries the line and column, so it is kept verbatim.
            where = f" in {path}" if path else ""
            raise ValueError(f"Could not parse{where}: {e}") from e

        if raw is None:
            raw = {}
        if not isinstance(raw, dict):
            raise ValueError(
                "A study file must be a mapping of header keys and section "
                f"names, not {type(raw).__name__}."
            )

        sections = {k: v for k, v in raw.items() if k in SECTIONS}
        extra = {
            k: v for k, v in raw.items() if k not in SECTIONS and k not in HEADER_KEYS
        }
        return cls(
            org=raw.get("org"),
            slug=raw.get("slug"),
            name=raw.get("name"),
            sections=sections,
            extra=extra,
            path=path,
        )

    @classmethod
    def load(cls, path: str) -> "StudyFile":
        with open(path, "r", encoding="utf8") as f:
            return cls.loads(f.read(), path=path)

    @classmethod
    def from_confs(
        cls,
        org: str,
        slug: str,
        confs: Mapping[str, Any],
        name: Optional[str] = None,
        path: Optional[str] = None,
    ) -> "StudyFile":
        """Build a file from what `GET /confs` returned.

        Unrecognised conf types go into `extra` rather than being dropped: the
        table has no constraint on `conf_type`, so a row written by something
        other than the nine routes is possible, and losing it on a pull/push
        round trip would be worse than carrying it.
        """
        sections = {k: v for k, v in confs.items() if k in SECTIONS}
        extra = {k: v for k, v in confs.items() if k not in SECTIONS}
        return cls(
            org=org, slug=slug, name=name, sections=sections, extra=extra, path=path
        )

    # -- writing -----------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Header first, then sections in canonical order, then anything else."""
        out: Dict[str, Any] = {}
        for key in HEADER_KEYS:
            value = getattr(self, key)
            if value is not None:
                out[key] = value
        for name in SECTIONS:
            if name in self.sections:
                out[name] = self.sections[name]
        for name in sorted(self.extra):
            out[name] = self.extra[name]
        return out

    def dumps(self, as_json: bool = False) -> str:
        data = self.to_dict()
        if as_json:
            return json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n"
        # `sort_keys=False` is the whole point: `to_dict` already ordered
        # things the way a reader wants them and alphabetising would put
        # `audiences` above `general`. `default_flow_style=False` keeps nested
        # Meta targeting blobs readable as block YAML rather than one long
        # line. `allow_unicode` so a Spanish creative body stays legible
        # instead of becoming escape sequences.
        return yaml.safe_dump(
            data, sort_keys=False, default_flow_style=False, allow_unicode=True
        )

    def save(self, path: Optional[str] = None) -> str:
        target = path or self.path
        if target is None:
            raise ValueError("No path to save to.")
        as_json = os.path.splitext(target)[1].lower() == ".json"
        with open(target, "w", encoding="utf8") as f:
            f.write(self.dumps(as_json=as_json))
        self.path = target
        return target

    # -- convenience -------------------------------------------------------

    def all_sections(self) -> Dict[str, Any]:
        """`sections` plus anything unrecognised, for the validator.

        `validate_study` has a `section.unrecognized` warning and it is the only
        thing in the system that will ever notice a typo'd section name: the
        server has no route for one, so a `stratas:` key is not written, not
        rejected, and not missed -- the study simply has no strata and nothing
        says why. Filtering the extras out before validating would throw away
        the one report that catches it.
        """
        return {**self.sections, **self.extra}

    def require_target(self) -> Tuple[str, str]:
        """`(org, slug)` from the header, or a message saying which is missing."""
        missing = [k for k in ("org", "slug") if not getattr(self, k)]
        if missing:
            where = f" in {self.path}" if self.path else ""
            raise ValueError(
                f"The study file is missing {' and '.join(missing)}{where}. "
                "Add them at the top of the file, or run `vlab create` which "
                "writes them for you."
            )
        return str(self.org), str(self.slug)


# ---------------------------------------------------------------------------
# The skeleton
# ---------------------------------------------------------------------------

# Written as literal text, not `yaml.safe_dump` of a dict, so that it can carry
# comments. A skeleton whose every field is annotated with the trap attached to
# it is worth a great deal more than one that is merely syntactically valid,
# and the traps are not guessable: `ad_account` without the `act_` prefix and
# `FacebookState` raises; `whatsapp_phone_number` is the number and not the
# `phone_number_id`; `template` is stored verbatim and must not be tidied.
#
# The values are real enough to POST once the placeholders are replaced, and
# the study it describes is the simplest one that recruits: one campaign, one
# Messenger destination, one creative, one stratum.
_SKELETON = """\
# A vlab study, as a file. See documentation/agent-api.md for every field.
#
#   vlab validate study.yaml     check it, locally and instantly
#   vlab diff     study.yaml     what would change on the server
#   vlab push     study.yaml     write the sections that differ
#
# Sections are the wire shapes verbatim: what `POST /confs/<type>` takes and
# what `GET /confs` gives back. Writing a section REPLACES it whole -- there is
# no partial update and no delete (study_confs is append-only).
#
# QUOTE YOUR STRINGS. This is YAML 1.1, where a bare `NO` is the boolean false,
# not Norway -- so `countries: [NO]` silently targets nothing. `y`, `on`, `off`
# and a bare number-like string are the same trap. Anything vlab writes back is
# quoted for you; anything you type by hand is not.

org: {org}
slug: {slug}
name: {name}

general:
  name: {name}
  # Must match a `credentials.key` row you own. `vlab meta credentials` lists
  # them; "Facebook" / "facebook" is what the dashboard hardcodes.
  credentials_key: Facebook
  credentials_entity: facebook
  # The BARE number. `vlab meta adaccounts` -> `account_id`, not `id`:
  # FacebookState raises outright if the `act_` prefix is present.
  ad_account: "REPLACE-ME"
  # Hours. The lookback the optimizer uses for spend and performance.
  opt_window: 48
  extra_metadata: {{}}

# An untagged three-way union until PR #262, tagged after it. Write `type`
# either way: an older server ignores it, a newer one uses it, and it stops
# the arms being told apart by which fields happen to be present.
recruitment:
  type: simple
  ad_campaign_name: {slug}
  objective: OUTCOME_ENGAGEMENT
  optimization_goal: LINK_CLICKS
  min_budget: 100
  budget: 10000
  max_sample: 1000
  # THE ON/OFF SWITCH. The crons only touch studies where
  # start_date < now < end_date. Write this section LAST.
  start_date: "2026-01-01T00:00:00"
  end_date: "2026-03-01T00:00:00"

destinations:
  - type: messenger
    name: main
    initial_shortcode: REPLACEME
    welcome_message: Welcome!
    button_text: Start

creatives:
  - name: creative-a
    destination: main
    # The creative blob off an existing Meta ad, stored VERBATIM.
    #   vlab meta ads --campaign <template campaign id> --json
    # Do not reshape it: adopt diffs the stored blob against the live ad field
    # by field, and an "improved" blob is a perpetual no-op rewrite.
    template: {{}}

audiences: []

# Inert on the server -- nothing reads it. It exists so the dashboard, and
# `vlab strata generate`, can derive strata from it.
variables: []

# The real configuration. `id` becomes the Meta ad set NAME, so renaming one
# deletes the ad set and creates a new one, losing its learning and history.
strata:
  - id: everyone
    quota: 1.0
    creatives:
      - creative-a
    audiences: []
    excluded_audiences: []
    facebook_targeting:
      geo_locations:
        countries:
          # Quoted deliberately: an unquoted two-letter code is a YAML 1.1
          # trap, and `NO` in particular parses as the boolean false.
          - "NG"
      targeting_automation:
        advantage_audience: 0
    question_targeting:
      op: answered
      vars:
        - type: variable
          value: REPLACE-with-your-finish-question-ref
    metadata: {{}}

data_sources: []

# Keys here must equal a `data_sources[].name`. Every variable named in a
# stratum's question_targeting must appear as an extraction_confs[].name.
inference_data:
  data_sources: {{}}
"""


def _yaml_scalar(value: str) -> str:
    """`value` as a YAML scalar that means exactly `value`.

    The skeleton is interpolated text, not a dumped dict, so nothing quotes for
    us -- and a study NAME is arbitrary user input that lands in two scalar
    positions. Unquoted, `"HPV: Lagos 2026"` makes the file unparseable, `"#1
    study"` reads as a comment and leaves `general.name` null, and `"Yes"` reads
    as the boolean true and is pushed as `name: true`. All three are ordinary
    study names, and `vlab create --init` is the first command in the runbook,
    by which point the study already exists server-side -- so a broken file is
    not recoverable by re-running.

    `json.dumps` rather than `yaml.safe_dump`: a JSON string is always a valid
    YAML double-quoted scalar, it never wraps or emits a block scalar, and it
    keeps the output on one line where the template expects one.
    """
    return json.dumps(value, ensure_ascii=False)


def skeleton(org: str = "REPLACE-ME", slug: str = "REPLACE-ME", name: str = "") -> str:
    """A commented, ready-to-edit study file."""
    return _SKELETON.format(
        # `org` is a UUID and `slug` is server-derived from the slug alphabet,
        # so neither can need quoting -- but they go through the same function
        # so that nobody has to re-derive that argument when editing this.
        org=_yaml_scalar(org),
        slug=_yaml_scalar(slug),
        name=_yaml_scalar(name or slug),
    )
