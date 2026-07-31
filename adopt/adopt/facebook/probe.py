"""Check the field contract against live Facebook ads.

    adopt-probe <study-id-or-name>            # read-only report
    adopt-probe <study-id-or-name> --update   # also rewrite DROPPED

For every field in field_contract.COMPARED_AD, this builds the creative the
study config says an ad should have — the same way `adset_instructions` does —
fetches the live ad, and classifies each leaf path:

    ok       we sent it, Facebook echoed it back unchanged
    dropped  we sent it, Facebook did not return it at all
    differs  we sent it, Facebook returned something else
    stale    declared DROPPED, but Facebook does return it now

`dropped` paths that are not declared are what cause endless rewrites, so they
are the point of this tool. `--update` writes them into field_contract.DROPPED
with today's date; review the git diff as you would any other change.

Read-only by default: it points at ads that are spending real money.
"""

import argparse
import json
import logging
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from environs import Env

from ..malaria import hydrate_strata, load_basics
from ..marketing import create_creative, pair_creatives_with_destinations
from ..study_conf import StudyConf
from . import field_contract
from .state import FacebookState

logger = logging.getLogger(__name__)

OK = "ok"
DROPPED = "dropped"
DIFFERS = "differs"

CONTRACT_PATH = Path(field_contract.__file__)
BEGIN = "# BEGIN DROPPED (managed by adopt-probe)"
END = "# END DROPPED (managed by adopt-probe)"


def _unwrap(x: Any) -> Any:
    """Facebook SDK objects and plain dicts both show up; normalise to dicts."""
    try:
        return x.export_all_data()
    except AttributeError:
        return x


def classify(
    desired: Any, source: Any, fields: List[str]
) -> List[Tuple[str, str, Any, Any]]:
    """Walk `fields` of desired vs source, returning (path, verdict, want, got).

    Mirrors how reconciliation._eq traverses, but reports every leaf instead of
    short-circuiting on the first difference — the whole point is to see all of
    them at once.
    """
    findings: List[Tuple[str, str, Any, Any]] = []

    d, s = _unwrap(desired), _unwrap(source)
    if not isinstance(d, dict) or not isinstance(s, dict):
        return findings

    for f in fields:
        if f not in d:
            continue
        if f not in s:
            findings.append((f".{f}", DROPPED, d[f], None))
            continue
        findings.extend(_walk(d[f], s[f], f".{f}"))

    return findings


def _walk(want: Any, got: Any, path: str) -> List[Tuple[str, str, Any, Any]]:
    want, got = _unwrap(want), _unwrap(got)

    if isinstance(want, dict) and isinstance(got, dict):
        out: List[Tuple[str, str, Any, Any]] = []
        for k, v in want.items():
            if k not in got:
                out.append((f"{path}.{k}", DROPPED, v, None))
                continue
            out.extend(_walk(v, got[k], f"{path}.{k}"))
        return out

    # Lists and scalars are compared whole. Facebook reorders lists, so sort
    # them the same way _eq does before comparing.
    if isinstance(want, list) and isinstance(got, list):
        key = lambda x: json.dumps(x, sort_keys=True, default=str)  # noqa: E731
        same = len(want) == len(got) and sorted(want, key=key) == sorted(got, key=key)
        return [(path, OK if same else DIFFERS, want, got)]

    return [(path, OK if want == got else DIFFERS, want, got)]


def probe_study(study: StudyConf, state: FacebookState) -> List[Tuple[str, str, Any, Any]]:
    """Classify every compared field across every live ad in the study."""
    strata = hydrate_strata(state, study.strata, study.creatives)
    by_id = {s.id: s for s in strata}
    fields = list(field_contract.COMPARED_AD)

    findings: List[Tuple[str, str, Any, Any]] = []

    for campaign_name in study.campaign_names:
        try:
            cs = state.campaign_state(campaign_name)
            live = cs.campaign_state
        except Exception as e:
            logger.warning(f"skipping campaign {campaign_name}: {e}")
            continue

        for adset, ads in live:
            stratum = by_id.get(_unwrap(adset).get("name"))
            if stratum is None:
                continue

            pairs = pair_creatives_with_destinations(study, stratum, campaign_name)
            desired = {
                c.name: create_creative(study, stratum, c, d) for c, d in pairs
            }

            for ad in ads:
                a = _unwrap(ad)
                want = desired.get(a.get("name"))
                if want is None or "creative" not in a:
                    continue
                findings.extend(classify(want, a["creative"], fields))

    return findings


def summarise(findings) -> Dict[str, Dict[str, Any]]:
    """Collapse per-ad findings into one row per path."""
    counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    examples: Dict[str, Tuple[Any, Any]] = {}

    for path, verdict, want, got in findings:
        counts[path][verdict] += 1
        if verdict != OK and path not in examples:
            examples[path] = (want, got)

    rows = {}
    for path, c in counts.items():
        # A path is only "clean" if it was clean on every ad.
        verdict = OK
        if c.get(DIFFERS):
            verdict = DIFFERS
        elif c.get(DROPPED):
            verdict = DROPPED

        declared = field_contract.is_dropped(path)
        rows[path] = {
            "verdict": verdict,
            "declared_dropped": declared,
            "ads": sum(c.values()),
            "hits": c.get(verdict, 0),
            "example": examples.get(path),
        }

    # Declared drops that Facebook now echoes back are stale declarations.
    for path, row in rows.items():
        if row["declared_dropped"] and row["verdict"] != DROPPED:
            row["verdict"] = "stale"

    return rows


def render(rows: Dict[str, Dict[str, Any]]) -> str:
    undeclared = sorted(
        p for p, r in rows.items() if r["verdict"] == DROPPED and not r["declared_dropped"]
    )
    declared = sorted(
        p for p, r in rows.items() if r["verdict"] == DROPPED and r["declared_dropped"]
    )
    differs = sorted(p for p, r in rows.items() if r["verdict"] == DIFFERS)
    stale = sorted(p for p, r in rows.items() if r["verdict"] == "stale")
    ok = sorted(p for p, r in rows.items() if r["verdict"] == OK)

    out = []
    out.append(f"compared {len(rows)} field paths across live ads\n")

    if undeclared:
        out.append("UNDECLARED DROPS — these cause a rewrite every run:")
        for p in undeclared:
            out.append(f"  {p}  ({rows[p]['hits']}/{rows[p]['ads']} ads)")
        out.append("  declare them with --update, or stop sending them\n")

    if differs:
        out.append("VALUE DIFFERS — a real change, will be rewritten once:")
        for p in differs:
            want, got = rows[p]["example"] or (None, None)
            out.append(f"  {p}\n    want={want!r}\n    got ={got!r}")
        out.append("")

    if stale:
        out.append("STALE DECLARATIONS — Facebook returns these now, undeclare them:")
        for p in stale:
            out.append(f"  {p}")
        out.append("")

    if declared:
        out.append(f"declared drops, still dropped: {len(declared)}")
        for p in declared:
            out.append(f"  {p}")
        out.append("")

    out.append(f"clean: {len(ok)} paths")

    if not undeclared and not differs and not stale:
        out.append("\ncontract matches live Facebook behaviour.")

    return "\n".join(out)


def render_dropped_block(paths: Dict[str, str]) -> str:
    """Regenerate the DROPPED literal between the markers."""
    lines = [BEGIN, "DROPPED: Dict[str, str] = {"]
    for path in sorted(paths):
        why = paths[path]
        lines.append(f'    "{path}": (')
        for chunk in _wrap(why, 74):
            lines.append(f'        "{chunk}"')
        lines.append("    ),")
    lines.append("}")
    lines.append(END)
    return "\n".join(lines)


def _wrap(text: str, width: int) -> List[str]:
    """Wrap `text` into string-literal chunks, keeping a trailing space."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + len(w) + 1 > width:
            lines.append(cur + " ")
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines or [""]


def update_contract(rows: Dict[str, Dict[str, Any]], today: str) -> Optional[str]:
    """Rewrite DROPPED to match what the probe just saw. Returns new file text."""
    keep = {
        p: why
        for p, why in field_contract.DROPPED.items()
        # Drop declarations Facebook has started honouring again.
        if rows.get(f".{p}", {}).get("verdict") != "stale"
    }

    for path, row in rows.items():
        if row["verdict"] == DROPPED and not row["declared_dropped"]:
            keep[path.lstrip(".")] = (
                f"Sent by adopt, absent from Facebook's response. "
                f"Confirmed live {today} by adopt-probe."
            )

    if keep == field_contract.DROPPED:
        return None

    text = CONTRACT_PATH.read_text()
    block = render_dropped_block(keep)
    new = re.sub(
        re.escape(BEGIN) + r".*?" + re.escape(END), block, text, flags=re.DOTALL
    )
    return new if new != text else None


def resolve_study_id(db_conf, ident: str) -> str:
    """Accept either a study id or a study name."""
    from ..db import query  # local import: keeps module import cheap for tests

    rows = query(db_conf, "select id from studies where id::text = %s", [ident])
    if rows:
        return ident

    rows = query(db_conf, "select id from studies where name = %s", [ident])
    if not rows:
        raise SystemExit(f"no study with id or name {ident!r}")
    if len(rows) > 1:
        raise SystemExit(f"{ident!r} matches {len(rows)} studies — pass the id")
    return str(rows[0][0])


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="adopt-probe", description="Check the field contract against live ads."
    )
    parser.add_argument("study", help="study id or name")
    parser.add_argument(
        "--update",
        action="store_true",
        help="rewrite field_contract.DROPPED to match what was found",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    env = Env()
    db_conf = env("PG_URL")

    study_id = resolve_study_id(db_conf, args.study)
    study, state = load_basics(study_id, db_conf, env)

    findings = probe_study(study, state)
    if not findings:
        print("no live ads matched this study's config — nothing to compare")
        return 0

    rows = summarise(findings)

    if args.json:
        print(
            json.dumps(
                {p: {k: v for k, v in r.items() if k != "example"} for p, r in rows.items()},
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(render(rows))

    if args.update:
        new = update_contract(rows, date.today().isoformat())
        if new is None:
            print("\nfield_contract.DROPPED already matches — nothing written")
        else:
            CONTRACT_PATH.write_text(new)
            print(f"\nwrote {CONTRACT_PATH} — review the diff")

    dirty = any(
        r["verdict"] == DROPPED and not r["declared_dropped"] or r["verdict"] == "stale"
        for r in rows.values()
    )
    return 1 if dirty and not args.update else 0


if __name__ == "__main__":
    sys.exit(main())
