"""`GET /{org_id}/studies/{slug}/strata-progress` -- the optimizer's own plan.

Phase B of `planning/mcp-full-coverage.md`. This is the dashboard's
"Participants per Segment" table, which until now existed ONLY on the Go
dashboard API (`GET /{org}/studies/{slug}/segments-progress`,
`api/internal/storage/studysegments.go`) -- an Auth0-only service, so no API
key and therefore no agent could ever read it. Everything it shows is already
in `adopt_reports`; the gap was a door, not data.

NOT THE GO PATH NAME, DELIBERATELY. This service already serves
`segments-progress`, and it is a different payload entirely (cumulative
participants over time, `server.get_segments_progress`). Two routes with one
name and two shapes is the trap the dashboard already lives with -- it calls
both, from two hosts -- and reproducing it here would make the payload depend
on which host you happened to ask.

WHAT THIS ADDS OVER THE GO ROUTE

* Every fact the report holds, not the seven Go declares: `total_spent`,
  `lifetime_spent`, `efficiency_weight` and the two counterfactuals are in
  every report and Go silently drops them (its `details` struct simply has no
  field for them).
* snake_case, matching the report's own keys and this service's other reads,
  rather than Go's camelCase for the dashboard's TypeScript.
* Unrounded numbers. Go rounds every percentage to two decimal places for
  display and then computes the deviation from the ROUNDED pair. An agent is
  not a table cell: it gets the report's own float, and
  `percentage_deviation_from_goal` is `abs(desired - current)` on the raw
  values. This is a deliberate divergence, not an oversight -- the two answers
  differ in the third decimal and only the raw one can be summed or compared
  across runs.
* `?history=N`, newest first, so an agent can see how budget MOVED. Go returns
  every report ever written, ascending, with no bound at all; a study a year
  into recruitment has thousands of runs, and no agent wants them by accident.

NO `desired_participants`. Go declares it (`*int64`, nullable) and reads it out
of the report if it is there. It never is: `budget.py`'s `report_facts` list is
the exhaustive set of keys `make_report` writes, and the only participant facts
in it are `current_participants` and `expected_participants`. Adding a field
that is always `null` would be inventing a promise the optimizer does not make.
"""

import asyncio
import logging
from datetime import timezone
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..campaign_queries import get_adopt_reports
from .db import db_cnf, get_study_id
from .deps import User, get_current_user

router = APIRouter()

# One report is what "the current allocation" means, and it is what the
# dashboard's table shows. The ceiling exists so that `?history=100000` is a
# 422 rather than a query that materialises every plan run a year-old study
# ever had; 200 is roughly a fortnight of the two-hourly adopt-ads cron.
DEFAULT_HISTORY = 1
MAX_HISTORY = 200


class StratumProgress(BaseModel):
    """One stratum's row of one report.

    EVERY FIELD BUT `id` HAS A DEFAULT, and that is the whole error policy for
    this route. A report is JSONB written by whatever version of `budget.py`
    was deployed when the plan ran, so an old row can be missing a fact that
    exists today (`efficiency_weight` and the counterfactuals all postdate the
    earliest reports). A missing fact must not be a 500 on the whole study's
    history -- it is a zero, or a null for the two facts that are genuinely
    optional even now, and the handler logs what was missing.
    """

    id: str
    current_participants: int = 0
    desired_percentage: float = 0.0
    current_percentage: float = 0.0
    expected_percentage: float = 0.0
    expected_participants: float = 0.0
    current_budget: float = 0.0
    current_price_per_participant: float = 0.0
    total_spent: float = 0.0
    lifetime_spent: float = 0.0
    efficiency_weight: float = 0.0
    # The only two that are optional in a CURRENT report as well as an old one:
    # `budget.py` appends them to `report_facts` just when the corresponding
    # constraint binds, so `null` here means "the optimizer did not compute
    # one", which is not the same as zero.
    counterfactual_spend_to_fill_sample: Optional[float] = None
    counterfactual_participants_with_unlimited_budget: Optional[float] = None
    # Computed, not stored. See `_stratum`.
    percentage_deviation_from_goal: float = 0.0


class ReportProgress(BaseModel):
    """One plan run: when it happened, and what it decided per stratum."""

    created: str
    strata: List[StratumProgress]


class StrataProgressResponse(BaseModel):
    data: List[ReportProgress]


# The facts the model takes off the report, as opposed to `id` (the JSONB key)
# and `percentage_deviation_from_goal` (computed). Filtering to these is what
# lets a NEW fact appear in `report_facts` without this route 422ing on it --
# pydantic would ignore it anyway, but naming the set makes the omission
# deliberate and gives `_stratum` something to report as missing.
_REPORT_FACTS = frozenset(StratumProgress.model_fields) - {
    "id",
    "percentage_deviation_from_goal",
}


def _stratum(stratum_id: str, facts: Dict[str, Any]) -> StratumProgress:
    """One report entry as a row, with the deviation the dashboard shows.

    `percentage_deviation_from_goal` is `abs(desired - current)` on the RAW
    values. Go rounds both to two places first and subtracts the rounded pair
    (`storage/studysegments.go`); that is a display decision, and reproducing
    it here would mean an agent could not recover the real number from what it
    was given.
    """
    known = {k: v for k, v in facts.items() if k in _REPORT_FACTS}
    row = StratumProgress(id=stratum_id, **known)
    row.percentage_deviation_from_goal = abs(
        row.desired_percentage - row.current_percentage
    )
    return row


def _report(row: Dict[str, Any]) -> ReportProgress:
    details = row["details"] or {}

    strata = [
        _stratum(str(stratum_id), facts or {})
        for stratum_id, facts in sorted(details.items())
    ]

    # ONE warning per report, not one per stratum: a report written before a
    # fact existed is missing it for every stratum in it, and a study with 200
    # strata would otherwise put 200 identical lines in the log for one old
    # row. Aggregated over the strata for the same reason.
    missing = sorted(
        _REPORT_FACTS
        - {
            fact
            for facts in details.values()
            for fact in (facts or {})
            if fact in _REPORT_FACTS
        }
    )
    if missing and details:
        logging.warning(
            "strata-progress: report written at %s carries no %s; "
            "defaulting those. An old report predating a fact is normal.",
            row["created"],
            ", ".join(missing),
        )

    created = row["created"]
    # `adopt_reports.created` is TIMESTAMPTZ, so this is aware and the
    # `astimezone` is a normalisation rather than an assumption. The naive
    # branch is for a driver or a test fixture that hands one back anyway --
    # UTC is what the column stores either way, and stamping it is what makes
    # the string unambiguous. Same reasoning as `studies.py`'s `created`.
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)

    return ReportProgress(
        created=created.astimezone(timezone.utc).isoformat(), strata=strata
    )


@router.get(
    "/{org_id}/studies/{slug}/strata-progress",
    response_model=StrataProgressResponse,
    responses={
        200: {"description": "Successfully retrieved per-stratum progress"},
        401: {"description": "Unauthorized - Invalid or missing authentication token"},
        404: {"description": "Study not found, or no adopt report for it"},
        422: {"description": "history out of range"},
    },
)
async def strata_progress_endpoint(
    org_id: str,
    slug: str,
    user: Annotated[User, Depends(get_current_user)],
    history: int = Query(DEFAULT_HISTORY, ge=1, le=MAX_HISTORY),
) -> StrataProgressResponse:
    """Per-stratum budget, price and progress from the last N plan runs.

    Newest report first, and within a report the strata are sorted by id so
    that two runs can be read side by side.
    """
    # Belt and braces with the `Query(ge=..., le=...)` above, which only runs
    # when FastAPI parses a query string. `POST /mcp` calls this handler
    # DIRECTLY (`server/mcp_server.InProcessBackend`), so on that front door
    # the annotation enforces nothing and `history=-1` would reach psycopg as a
    # `LIMIT -1`. Same 422 either way. See `studies.list_studies_endpoint`.
    if not 1 <= history <= MAX_HISTORY:
        raise HTTPException(
            status_code=422,
            detail=(f"history must be between 1 and {MAX_HISTORY}; got {history}."),
        )

    study_id = get_study_id(user.user_id, org_id, slug)
    if not study_id:
        raise HTTPException(status_code=404, detail=f"Study not found: {slug}")

    # `to_thread` like its neighbours: psycopg is synchronous, and a report for
    # a study with hundreds of strata is not a cheap row to fetch or parse.
    rows = await asyncio.to_thread(get_adopt_reports, study_id, db_cnf, history)

    if not rows:
        # 404, not an empty list, and this is the one place this route differs
        # from `segments-progress` and `cost-over-time` next door. Those answer
        # `{"data": []}` because the dashboard draws an empty chart with it. An
        # agent asking for the current allocation and getting `[]` cannot tell
        # "no plan has ever run" from "the plan allocated nothing", and those
        # want opposite actions. Same sentence as `get_latest_adopt_report`
        # gives, with the SLUG: an agent is never handed a study id.
        raise HTTPException(
            status_code=404, detail=f"No adopt report found for study {slug}"
        )

    return StrataProgressResponse(data=[_report(row) for row in rows])
