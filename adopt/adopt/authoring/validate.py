"""Whole-study validation: assemble the nine sections and report everything.

Phase 3 of `planning/agent-study-authoring.md` §8, and the answer to §2.5 and
§11.4 item 4.

WHY THIS EXISTS
---------------

Every `POST /{org}/studies/{slug}/confs/<type>` parses *one* section against
*its* model and stores it. Nothing looks at any other section. The complete
`StudyConf` — the object that carries every cross-section invariant — is only
assembled later, by `malaria.get_study_conf` on the optimize path, which is
reached from a cron. So nine `201`s can leave a study that will never create an
ad, and the author finds out hours later in a log they cannot read.

Worse, the failures are not uniform (`documentation/agent-api.md` §1.3):

* a stratum naming a creative that does not exist is a bare `KeyError` out of a
  list comprehension in `malaria.hydrate_strata`, with no message
  naming the stratum — the whole study's reconciliation run dies;
* a creative naming a destination that does not exist is a clear `Exception`
  from `marketing.get_destination_for_creative` — and also kills the
  run;
* a stratum naming an audience that does not exist is **dropped at
  `logging.info`** (`malaria._add_aud`), where a dropped *exclusion*
  means the ad set quietly re-recruits people it meant to exclude;
* two whole-study checks are `logging.warning` calls nobody reads
  (`warn_on_incomplete_targeting`, `warn_on_thinned_ref_without_mapping`).

`validate_study` is the one place that asks all of those questions at once, off
the write path, and answers with a report rather than an exception.

WHAT IT IS NOT
--------------

Pure Python. It reads no database and calls no Meta API, so it can run in an
SDK on an author's laptop against sections that have never been written. That
bounds what it can check — see `KNOWN_GAPS` at the bottom of this module, and
`planning/agent-study-authoring.md` §10, which proposes a separate
`vlab check --live` for the Meta-dependent half.

COLLECT, DO NOT STOP
--------------------

An author wants one list of everything wrong, not a game of whack-a-mole. So:
pydantic already returns every field error in a section at once, each section
is parsed independently of the others, and the cross-section checks run on
whatever parsed — a study with a broken `recruitment` conf still gets told
about its dangling creative references.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from pydantic import BaseModel, TypeAdapter, ValidationError

from ..study_conf import (
    AudienceConf,
    CreativeConf,
    DataSourceConf,
    DestinationConf,
    GeneralConf,
    InferenceDataConf,
    RecruitmentConf,
    StratumConf,
    StudyConf,
    UserInfo,
    VariableConf,
    supplied_variables,
    targeting_variables,
)

# ---------------------------------------------------------------------------
# The sections
# ---------------------------------------------------------------------------

# Keyed by conf type AS STORED, i.e. the `study_confs.conf_type` value, which is
# the URL segment with hyphens turned into underscores: `confs/data-sources`
# stores `data_sources` (see `documentation/agent-api.md` §3). `get_all_study_confs`
# returns exactly these keys, so a stored study drops straight in.
#
# The models are the ones `StudyConf` assembles from and the ones the POST
# routes in `server/server.py` annotate their bodies with. They are named here
# rather than introspected off the routes deliberately: what makes a study
# *run* is what `StudyConf` accepts, and if a write path ever gets stricter than
# the run path (a live proposal — §11.4 item 2, `extra="ignore"`) this table
# must keep following the run path, or a report would call a study broken that
# reconciles perfectly well.
SECTION_MODELS: Dict[str, Any] = {
    "general": GeneralConf,
    "recruitment": RecruitmentConf,
    "destinations": List[DestinationConf],
    "creatives": List[CreativeConf],
    "audiences": List[AudienceConf],
    "variables": List[VariableConf],
    "strata": List[StratumConf],
    "data_sources": List[DataSourceConf],
    "inference_data": InferenceDataConf,
}

SECTIONS: Tuple[str, ...] = tuple(SECTION_MODELS)

# The sections `StudyConf` declares without a default. Absent any one of them,
# assembly raises and the cron cannot run the study at all, so they are errors
# rather than warnings even though a study mid-authoring will legitimately be
# missing some. `variables` is not here because it is inert on the server
# (§1.5); `inference_data` and `data_sources` are `Optional` on `StudyConf`.
REQUIRED_SECTIONS: Tuple[str, ...] = (
    "general",
    "recruitment",
    "destinations",
    "creatives",
    "audiences",
    "strata",
)

_ADAPTERS = {name: TypeAdapter(model) for name, model in SECTION_MODELS.items()}


# ---------------------------------------------------------------------------
# The report
# ---------------------------------------------------------------------------


class ValidationMessage(BaseModel):
    """One finding.

    `code` is the machine-readable half and is the part a client should branch
    on; `message` is prose and may be reworded. `section` is the stored conf
    type the finding is about (`None` only when it is about the study as a
    whole), and `path` addresses the offending value inside it in the
    `strata[0].creatives[1]` style — `None` when the finding is not attributable
    to one value.
    """

    code: str
    section: Optional[str] = None
    path: Optional[str] = None
    message: str


class ValidationReport(BaseModel):
    """Everything wrong with a study, in one pass.

    `valid` is `not errors`. Warnings never make a study invalid: every one of
    them describes something that will run and may well be intended — see the
    reasoning on `missing_targeting_variables` and
    `thins_its_ref_without_reading_the_mapping` in `study_conf.py`, which is
    why those two are `logging.warning` at run time and not raises.
    """

    valid: bool
    errors: List[ValidationMessage] = []
    warnings: List[ValidationMessage] = []


def _path(section: Optional[str], loc: Sequence[Any] = ()) -> Optional[str]:
    """A pydantic `loc` rendered as a JSON-ish path, rooted at the section.

    `("strata", 0, "quota")` -> `strata[0].quota`. Ints index, strings key. The
    section name leads so that a path is meaningful on its own, which matters
    because the report is flat and a client is likely to show only this.
    """
    if section is None:
        return None

    out = section
    for part in loc:
        out += f"[{part}]" if isinstance(part, int) else f".{part}"
    return out


# ---------------------------------------------------------------------------
# Assembly — the one shared with the run path
# ---------------------------------------------------------------------------

# `StudyConf` carries two fields that are not stored conf sections: `id`, off
# the studies row, and `user`, resolved from the `credentials` table at run time
# by `get_user_info`. Validation is pure and offline, so it supplies stand-ins.
#
# That is safe, and it is worth saying why rather than hoping: no validator on
# `StudyConf` reads either field. `check_whatsapp_refs_are_deliverable` touches
# `destinations`, `creatives`, `strata` and `general` only, and `id` is read at
# ad-creation time (`mint_ref_token`), long after validation. If a future
# validator does read `user`, this stand-in makes it vacuous rather than wrong —
# and the credential check it would want is a database read this function
# cannot do anyway (see KNOWN_GAPS).
VALIDATION_USER = UserInfo(survey_user="validate", token="validate")
VALIDATION_STUDY_ID = "00000000-0000-0000-0000-000000000000"


def study_conf_from_sections(
    sections: Mapping[str, Any],
    study_id: str = VALIDATION_STUDY_ID,
    # A `UserInfo`, or the raw row `get_user_info` returns — pydantic coerces
    # the dict, which is what the run path has always relied on.
    user: Any = None,
) -> StudyConf:
    """Build a `StudyConf` from the nine stored sections plus id and user.

    Factored out of `malaria.get_study_conf`, which now calls it, so that the
    validator and the run path assemble a study exactly the same way. There is
    no second definition of "these sections become a study" to drift.

    `sections` are keyed by stored conf type and hold wire values (what
    `get_all_study_confs` returns), or already-parsed models — pydantic accepts
    either. Unknown keys are ignored, which is how `variables` has always been
    handled: it is stored, it is passed in, and `StudyConf` does not declare it
    (§1.5).
    """
    return StudyConf(
        id=str(study_id),
        user=user if user is not None else VALIDATION_USER,
        **dict(sections),
    )


# ---------------------------------------------------------------------------
# Audience naming
# ---------------------------------------------------------------------------

_COHORT = re.compile(r"^(?P<name>.+)-cohort-(?P<n>[1-9][0-9]*)$")


def audience_names_created_by(conf: AudienceConf) -> List[str]:
    """The Meta custom-audience names this conf will ever create.

    Mirrors `audiences.hydrate_audience`, which is the only thing that names
    them:

        CUSTOM      -> `<name>`
        LOOKALIKE   -> `<name>-origin`, and `<name>` once the origin holds
                       `lookalike.target` users
        PARTITIONED -> `<name>-cohort-1`, `-cohort-2`, ... and **never**
                       a plain `<name>`

    The cohort count is data-dependent (it is however many partitions the
    respondents divide into), so the partitioned case cannot be enumerated here
    and is matched by pattern in `_audience_reference_finding` instead.
    """
    if conf.subtype == "LOOKALIKE":
        return [f"{conf.name}-origin", conf.name]
    if conf.subtype == "PARTITIONED":
        return []
    return [conf.name]


def _audience_reference_finding(
    name: str,
    audiences: Sequence[AudienceConf],
    section: str,
    path: Optional[str],
    excluded: bool,
) -> Optional[ValidationMessage]:
    """Classify one `strata[].audiences[]` / `excluded_audiences[]` entry.

    **Every finding here is a warning.** `strata[].audiences` does not point at
    `audiences[].name`: it points at a custom audience **on the Meta ad
    account**, matched by name (`FacebookState.get_audience`), and that account
    may hold audiences built by hand in Ads Manager or by another study. A pure,
    offline validator cannot tell a typo from a legitimate external audience —
    only a live check against Meta can, which is the `vlab check --live` split
    proposed in `planning/agent-study-authoring.md` §10.

    `audience.partitioned_bare_name` is the sharpest of them and was an error in
    the first draft: the name IS an `audiences[].name` in this study, that conf
    is `PARTITIONED`, and vlab therefore creates `<name>-cohort-N` and never
    `<name>` — the case §11.4 item 4 singles out, and one where the author's
    intent is not in doubt. Review demoted it, correctly: the rule above admits
    no exception. `get_audience` matches on the ad account, so an audience
    someone built by hand under exactly that name would resolve, and the
    validator cannot see that it did not. The message stays sharp; only the
    severity moved.

    (Over HTTP this finding is currently unreachable, because an `AudienceConf`
    with `subtype: "PARTITIONED"` cannot be parsed from JSON at all — its
    `mode="before"` validator isinstance-checks `partitioning` against the
    parsed `Partitioning` class before pydantic has parsed anything, so the
    section is reported as `section.invalid` first. That bug is being fixed
    separately in `study_conf.py`; this check is already correct for the day it
    lands, and is reachable now from Python objects, which is how an SDK will
    hand a study over.)
    """
    created = {n for a in audiences for n in audience_names_created_by(a)}
    if name in created:
        return None

    partitioned = {a.name for a in audiences if a.subtype == "PARTITIONED"}

    if name in partitioned:
        return ValidationMessage(
            code="audience.partitioned_bare_name",
            section=section,
            path=path,
            message=(
                f"Audience '{name}' is a PARTITIONED audience conf, which vlab "
                f"names '{name}-cohort-1', '{name}-cohort-2', ... and never "
                f"'{name}'. This reference can never resolve: it will be "
                "dropped at INFO level and the stratum will target "
                + ("without the exclusion" if excluded else "unfiltered")
                + ". Name a specific cohort instead."
            ),
        )

    cohort = _COHORT.match(name)
    if cohort and cohort.group("name") in partitioned:
        # `<name>-cohort-N` for a partitioned conf. Whether cohort N exists yet
        # depends on how many respondents have arrived, so this is as far as
        # offline validation goes.
        return None

    return ValidationMessage(
        code=(
            "stratum.excluded_audience_unknown"
            if excluded
            else "stratum.audience_unknown"
        ),
        section=section,
        path=path,
        message=(
            f"Audience '{name}' is not created by this study's audiences conf. "
            "Audience references resolve against custom audiences on the Meta "
            "ad account by name, so this is only a problem if no such audience "
            "exists there — vlab cannot tell offline. If it does not resolve, "
            + (
                "the exclusion is dropped at INFO level and the ad set will "
                "re-recruit people it meant to exclude."
                if excluded
                else "it is dropped at INFO level and the stratum targets "
                "more broadly than intended."
            )
        ),
    )


# ---------------------------------------------------------------------------
# The cross-section checks
# ---------------------------------------------------------------------------
#
# Each takes only the sections it needs, and each is a no-op when one of them is
# missing or failed to parse. That is what lets a report cover a half-written
# study: an author with a broken `recruitment` conf still learns that three
# strata name a creative that does not exist.


def _check_creative_references(
    strata: Sequence[StratumConf], creatives: Sequence[CreativeConf]
) -> List[ValidationMessage]:
    """`strata[].creatives[]` -> `creatives[].name`.

    A dangling name is a bare `KeyError` out of `malaria.hydrate_strata` that
    kills the whole study's reconciliation run and names neither the stratum nor
    the creative. Unambiguously an error: unlike audiences, this edge resolves
    entirely inside the study's own config, and every creative a stratum names
    is resolved unconditionally.
    """
    known = {c.name for c in creatives}
    out = []
    for i, stratum in enumerate(strata):
        for j, name in enumerate(stratum.creatives):
            if name not in known:
                out.append(
                    ValidationMessage(
                        code="stratum.creative_unknown",
                        section="strata",
                        path=_path("strata", (i, "creatives", j)),
                        message=(
                            f"Stratum '{stratum.id}' names creative '{name}', "
                            "which is not in the creatives conf. At run time "
                            "this is a bare KeyError in hydrate_strata that "
                            "aborts the whole study's reconciliation. "
                            f"Known creatives: {sorted(known)}."
                        ),
                    )
                )
    return out


def _check_destination_references(
    creatives: Sequence[CreativeConf],
    destinations: Sequence[DestinationConf],
    strata: Optional[Sequence[StratumConf]],
) -> List[ValidationMessage]:
    """`creatives[].destination` -> `destinations[].name`.

    Split in two by whether any stratum actually names the creative, which is
    the thing that decides whether a dangling destination is fatal.

    `get_destination_for_creative` (`marketing.get_destination_for_creative`)
    raises a clear `Exception`, and it kills the reconciliation run — but it has
    exactly one caller, `creative_destination_pairs`, and that caller iterates
    `stratum.creatives`, never the whole `creatives` conf. So a creative no
    stratum references is never resolved and its dead destination costs
    nothing: the study reconciles fine.

    Hence:

    ERROR (`creative.destination_unknown`) — a creative some stratum names.
    This is reached at run time and kills the study.

    WARNING (`creative.unreferenced_destination_unknown`) — a creative nothing
    names. Latent: harmless today, fatal the moment a stratum adds it.

    Why that narrow warning rather than a general `creative.unreferenced`: an
    unreferenced creative is ordinary editing debris, common and harmless, and
    warning about every one of them would bury the report in noise — which is
    the thing that stops anyone reading it. The pair of conditions is what makes
    a finding: unreferenced AND pointing at nothing.

    When `strata` is unavailable (missing, or it failed to parse) nothing can be
    known about which creatives are referenced, so every dangling destination is
    reported as the latent warning. Under-claiming is the right direction: an
    error the caller cannot act on is worse than a warning they can.
    """
    known = {d.name for d in destinations}
    referenced = (
        {name for s in strata for name in s.creatives} if strata is not None else set()
    )

    out = []
    for i, creative in enumerate(creatives):
        if creative.destination in known:
            continue

        if creative.name in referenced:
            out.append(
                ValidationMessage(
                    code="creative.destination_unknown",
                    section="creatives",
                    path=_path("creatives", (i, "destination")),
                    message=(
                        f"Creative '{creative.name}' names destination "
                        f"'{creative.destination}', which is not in the "
                        "destinations conf. A stratum names this creative, so "
                        "at run time this aborts the study's reconciliation. "
                        f"Known destinations: {sorted(known)}."
                    ),
                )
            )
        else:
            out.append(
                ValidationMessage(
                    code="creative.unreferenced_destination_unknown",
                    section="creatives",
                    path=_path("creatives", (i, "destination")),
                    message=(
                        f"Creative '{creative.name}' names destination "
                        f"'{creative.destination}', which is not in the "
                        "destinations conf. No stratum names this creative, so "
                        "nothing resolves it today and the study runs — but the "
                        "moment a stratum adds it, reconciliation aborts. "
                        f"Known destinations: {sorted(known)}."
                    ),
                )
            )
    return out


def _check_audience_references(
    strata: Sequence[StratumConf], audiences: Sequence[AudienceConf]
) -> List[ValidationMessage]:
    out = []
    for i, stratum in enumerate(strata):
        for field, excluded in (("audiences", False), ("excluded_audiences", True)):
            for j, name in enumerate(getattr(stratum, field)):
                finding = _audience_reference_finding(
                    name,
                    audiences,
                    "strata",
                    _path("strata", (i, field, j)),
                    excluded,
                )
                if finding:
                    out.append(finding)
    return out


def _check_stratum_ids_unique(strata: Sequence[StratumConf]) -> List[ValidationMessage]:
    """`malaria.uniqueness` raises on a duplicate, at run time only.

    Included because it is the same class of whole-study failure and free here:
    the run-time message ("Strata IDs combinations are not unique") does not say
    which id, and a stratum id is an ad set name, so a duplicate is also a
    reconciliation ambiguity.
    """
    seen: Dict[str, int] = {}
    out = []
    for i, stratum in enumerate(strata):
        if stratum.id in seen:
            out.append(
                ValidationMessage(
                    code="stratum.id_duplicated",
                    section="strata",
                    path=_path("strata", (i, "id")),
                    message=(
                        f"Stratum id '{stratum.id}' is already used at "
                        f"strata[{seen[stratum.id]}]. Ids must be unique — "
                        "`uniqueness` raises at run time, and a stratum id is "
                        "also the ad set's name on Meta."
                    ),
                )
            )
        else:
            seen[stratum.id] = i
    return out


def _check_targeting_variables(
    strata: Sequence[StratumConf], inference_data: Optional[InferenceDataConf]
) -> List[ValidationMessage]:
    """`warn_on_incomplete_targeting`, as a report instead of a log line.

    This is `study_conf.missing_targeting_variables` decomposed into
    its two pure halves, `targeting_variables` and `supplied_variables`, which
    are imported rather than reimplemented. The decomposition exists so the
    check can run on a study whose other sections did not parse;
    `test_validate.py` pins it against `missing_targeting_variables` on a
    complete study so the two cannot drift.

    It is also runbook step 8 in `documentation/agent-api.md` §6, which until
    now read "check, yourself, ... Nothing else will".

    A WARNING, not an error, and the reasoning is `missing_targeting_variables`'
    own: a study with no `inference_data` conf yet supplies nothing, so every
    targeted variable would look missing — that is an unfinished study, not a
    broken one — and the check has never been run against the thousands of
    existing production studies, so its false-positive rate is unmeasured.
    """
    supplied = supplied_variables(inference_data)
    out = []
    for i, stratum in enumerate(strata):
        missing = targeting_variables(stratum.question_targeting) - supplied
        if missing:
            out.append(
                ValidationMessage(
                    code="stratum.targeting_variable_unsupplied",
                    section="strata",
                    path=_path("strata", (i, "question_targeting")),
                    message=(
                        f"Stratum '{stratum.id}' targets variable(s) "
                        f"{sorted(missing)} that no inference_data extraction "
                        "conf produces. Its question_targeting can never match, "
                        "so it will count zero respondents and the optimizer "
                        "will move its budget elsewhere. Supplied variables: "
                        f"{sorted(supplied)}."
                    ),
                )
            )
    return out


def _check_thinned_refs(
    destinations: Sequence[DestinationConf],
    inference_data: Optional[InferenceDataConf],
) -> List[ValidationMessage]:
    """`warn_on_thinned_ref_without_mapping`, as a report instead of a log line.

    `study_conf.thins_its_ref_without_reading_the_mapping` decomposed the same
    way and for the same reason as
    `_check_targeting_variables`, and pinned against it by a test.

    A WARNING for the reason that function gives: a study recruiting uniformly,
    with no question_targeting anywhere, needs no stratum attribution and is
    entitled to a thin ref.
    """
    thinned = sorted(d.name for d in destinations if d.resolved_ref_mode != "metadata")
    if not thinned:
        return []

    reads_the_mapping = any(
        ec.is_ad_table_lookup
        for source in (inference_data.data_sources.values() if inference_data else [])
        for ec in source.extraction_confs
    )
    if reads_the_mapping:
        return []

    return [
        ValidationMessage(
            code="destination.thinned_ref_without_mapping",
            section="destinations",
            path=None,
            message=(
                f"Destination(s) {thinned} no longer carry stratum metadata in "
                "their ref, but this study has no inference_data conf with "
                'mapping: "ad_table_lookup". Nothing will attribute their '
                "respondents to a stratum: every stratum will count zero and "
                "the optimizer will reallocate on empty data. Either add the "
                "lookup confs, or set the destination's ref_mode to 'metadata'."
            ),
        )
    ]


def _check_inference_data_sources(
    inference_data: Optional[InferenceDataConf],
    data_sources: Optional[Sequence[DataSourceConf]],
) -> List[ValidationMessage]:
    """`inference_data.data_sources` keys -> `data_sources[].name`.

    The seventh edge of the reference graph (`documentation/agent-api.md` §1.3).
    swoosh skips events from a key that names no source and folds them into one
    aggregated extraction error (`inference/swoosh/inference_data.go:642`), so
    the failure is visible but only after respondents have already been lost.

    A WARNING rather than an error because this is swoosh's join, not adopt's:
    nothing in this repo's Python resolves it, the section is optional, and the
    consequence is dropped events rather than a dead study.
    """
    if inference_data is None or data_sources is None:
        return []

    known = {d.name for d in data_sources}
    out = []
    for key in inference_data.data_sources:
        if key not in known:
            out.append(
                ValidationMessage(
                    code="inference_data.source_unknown",
                    section="inference_data",
                    path=_path("inference_data", ("data_sources", key)),
                    message=(
                        f"inference_data names data source '{key}', which is "
                        "not in the data_sources conf. swoosh will skip every "
                        "event from it and report one aggregated extraction "
                        f"error. Known sources: {sorted(known)}."
                    ),
                )
            )
    return out


# ---------------------------------------------------------------------------
# The entry point
# ---------------------------------------------------------------------------


def _parse_sections(
    sections: Mapping[str, Any],
) -> Tuple[Dict[str, Any], set, List[ValidationMessage], List[ValidationMessage]]:
    """Parse each supplied section on its own.

    Returns `(parsed, failed, errors, warnings)`.

    Independently, so that one broken section does not hide the others' errors,
    and so the cross-section checks below get everything that did parse.

    `failed` is the set of sections that were supplied and did not parse, and it
    exists because "absent" and "unparseable" are NOT the same thing to a
    cross-section check even though both leave the section out of `parsed`. An
    absent `inference_data` supplies no variables, and every stratum targeting
    one is a genuine warning — that is a study not yet wired to a survey
    platform. An *unparseable* `inference_data` supplies no variables only
    because we could not read it, and warning that nothing is supplied would be
    noise piled on top of the `section.invalid` error that already says so.
    """
    parsed: Dict[str, Any] = {}
    failed: set = set()
    errors: List[ValidationMessage] = []
    warnings: List[ValidationMessage] = []

    for name, value in sections.items():
        if name not in SECTION_MODELS:
            warnings.append(
                ValidationMessage(
                    code="section.unrecognized",
                    section=None,
                    path=name,
                    message=(
                        f"'{name}' is not a study conf type and is ignored. "
                        f"The nine are: {', '.join(SECTIONS)}."
                    ),
                )
            )
            continue

        if value is None:
            # An explicit null means "as if never written" — see the overlay
            # semantics on the endpoint. Reported by the missing-section pass
            # below if the section is required.
            continue

        try:
            parsed[name] = _ADAPTERS[name].validate_python(value)
        except ValidationError as e:
            failed.add(name)
            errors.extend(
                ValidationMessage(
                    code="section.invalid",
                    section=name,
                    path=_path(name, err["loc"]),
                    message=err["msg"],
                )
                for err in e.errors()
            )
        except Exception as e:
            # Not defensive padding: `AudienceConf.__post_init__` does
            # `values["subtype"]` in a `mode="before"` validator, so an audience
            # with no `subtype` raises a bare `KeyError` that pydantic does not
            # wrap (it converts only ValueError and AssertionError). Without
            # this, validating an incomplete audience conf would crash the
            # validator — and, through the endpoint, return a 500 for a report
            # whose whole purpose is to describe bad input.
            failed.add(name)
            errors.append(
                ValidationMessage(
                    code="section.invalid",
                    section=name,
                    path=_path(name),
                    message=f"{type(e).__name__}: {e}",
                )
            )

    return parsed, failed, errors, warnings


def validate_study(sections: Mapping[str, Any]) -> ValidationReport:
    """Validate a whole study from its nine conf sections.

    `sections` is keyed by conf type as stored — `general`, `recruitment`,
    `destinations`, `creatives`, `audiences`, `variables`, `strata`,
    `data_sources`, `inference_data` — holding JSON wire values, exactly what
    `db.get_all_study_confs` returns and what the POST routes accept. A section
    may be absent, or present as `None`, which means the same thing.

    Never raises for bad input: everything it finds comes back in the report.
    """
    parsed, failed, errors, warnings = _parse_sections(sections)

    for name in REQUIRED_SECTIONS:
        if name in parsed:
            continue
        if name in sections and sections[name] is not None:
            # Present but unparseable: already reported as section.invalid.
            # Saying "missing" too would be two findings for one mistake.
            continue
        errors.append(
            ValidationMessage(
                code="section.missing",
                section=name,
                path=None,
                message=(
                    f"The '{name}' conf has never been written. StudyConf "
                    "declares it with no default, so the study cannot be "
                    "assembled and every cron run will fail before it starts."
                ),
            )
        )

    # The whole-study assembly, run only when every required section parsed —
    # otherwise pydantic would re-report the same field errors under a second
    # code. Anything that surfaces here is therefore cross-section by
    # construction: today that is `check_whatsapp_refs_are_deliverable`, and
    # anything added to StudyConf later comes along for free, which is the
    # reason this goes through the same function the run path uses rather than
    # enumerating the validators.
    if all(name in parsed for name in REQUIRED_SECTIONS):
        try:
            study_conf_from_sections(parsed)
        except ValidationError as e:
            errors.extend(
                ValidationMessage(
                    code="study.invalid",
                    section=None,
                    path=None,
                    message=err["msg"],
                )
                for err in e.errors()
            )
        except Exception as e:
            errors.append(
                ValidationMessage(
                    code="study.invalid",
                    section=None,
                    path=None,
                    message=f"{type(e).__name__}: {e}",
                )
            )

    strata = parsed.get("strata")
    creatives = parsed.get("creatives")
    destinations = parsed.get("destinations")
    audiences = parsed.get("audiences")
    inference_data = parsed.get("inference_data")
    data_sources = parsed.get("data_sources")

    # A check is skipped when a section it reads was SUPPLIED and did not parse
    # (`failed`), as opposed to simply being absent. For the two optional
    # sections the difference is invisible in `parsed` — both leave the value
    # None — and it changes the answer: an absent `inference_data` genuinely
    # supplies no variables, an unparseable one supplies none only because we
    # could not read it. Warning in the second case is noise stacked on top of
    # the `section.invalid` error that already says so, and noise is what stops
    # anyone reading the report. The required sections need no such guard: a
    # failed one is not in `parsed`, so the `is not None` tests already skip it.
    read_inference_data = "inference_data" not in failed
    read_data_sources = "data_sources" not in failed

    if strata is not None:
        errors += _check_stratum_ids_unique(strata)
        if read_inference_data:
            warnings += _check_targeting_variables(strata, inference_data)
        if creatives is not None:
            errors += _check_creative_references(strata, creatives)
        if audiences is not None:
            # Every audience finding is a warning; see
            # `_audience_reference_finding` for why, including the partitioned
            # case that review demoted.
            warnings += _check_audience_references(strata, audiences)

    if creatives is not None and destinations is not None:
        findings = _check_destination_references(creatives, destinations, strata)
        errors += [f for f in findings if f.code == "creative.destination_unknown"]
        warnings += [f for f in findings if f.code != "creative.destination_unknown"]

    if destinations is not None and read_inference_data:
        warnings += _check_thinned_refs(destinations, inference_data)

    if read_inference_data and read_data_sources:
        warnings += _check_inference_data_sources(inference_data, data_sources)

    return ValidationReport(valid=not errors, errors=errors, warnings=warnings)


# ---------------------------------------------------------------------------
# What this cannot see
# ---------------------------------------------------------------------------
#
# Documented as data so the endpoint and the SDK can show the same list rather
# than each writing its own. Every entry is a check that needs something this
# function deliberately does not have — a database, or Meta.
KNOWN_GAPS: Tuple[str, ...] = (
    "general.credentials_key is not checked against the credentials table: "
    "that is a database read, and a dangling key raises at load_basics time "
    "('Could not find credentials for study id: ...').",
    "data_sources[].credentials_key is likewise unchecked; a dangling one "
    "means the study is silently never collected (connector.go:83).",
    "Audience references are not checked against the ad account's real custom "
    "audiences, so an audience built by hand in Ads Manager is indistinguishable "
    "from a typo. Every audience finding is therefore a warning, including a "
    "stratum naming a PARTITIONED conf by a name vlab never creates.",
    "A LOOKALIKE audience's own `<name>` is accepted unconditionally, but "
    "`audiences.hydrate_audience` only creates it once the origin audience "
    "holds `lookalike.target` users -- until then only `<name>-origin` exists. "
    "That is a respondent count, not configuration, so it is out of reach here: "
    "a stratum may reference an audience that is correct and simply not built "
    "yet. The same is true of every audience reference on a study's first runs, "
    "before the audience cron has created anything.",
    "Nothing Meta-side is checked: whether the template campaign or ad set "
    "still exists, whether the creative template is still valid, or whether "
    "recruitment.objective and optimization_goal are a pairing Meta accepts. "
    "See planning/agent-study-authoring.md §10 — this is the "
    "`vlab check --live` half.",
    "The optimizer is not run: an assembled, valid study can still produce an "
    "empty instruction list. Use GET /{org}/optimize/{slug} for that.",
)
