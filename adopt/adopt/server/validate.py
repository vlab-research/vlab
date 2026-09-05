"""`POST /{org}/studies/{slug}/validate` — whole-study validation, writes nothing.

Phase 3 of `planning/agent-study-authoring.md` §8: "Also add
`POST /{org}/studies/{slug}/validate` to the server — whole-study assembly,
errors and warnings, writes nothing."

A THIN WRAPPER, DELIBERATELY
----------------------------

All of the thinking is in `adopt.authoring.validate.validate_study`, which is a
pure function over the nine sections. This module reads the stored confs,
applies an optional overlay, calls it, and serialises the report. That split is
the point: `vlab validate` in the SDK imports the library directly and must
agree with this endpoint by construction, not by a second implementation kept
in step by hand. An MCP client that cannot install Python gets the same answers
here.

WHY IT IS A POST THAT NEEDS ONLY `studies:read`
-----------------------------------------------

POST because the optional body carries a whole study's worth of proposed
sections, which does not belong in a query string. But it writes nothing at
all — no `study_confs` row, no report row, nothing — so classifying it by HTTP
method would demand `studies:write` for a pure read and a read-only key could
not check its own work. `api_keys.required_scope` pins this one path to
`studies:read`; see the comment there.

Contrast `GET /{org}/optimize/{slug}` (§2.6), the closest thing that existed
before: it is a GET and it *does* write — an adopt_reports row and two
time-series reports — as well as reading Meta and healing ad attributions. The
method has never been the guide on this service.

WHY 200 FOR AN INVALID STUDY
----------------------------

The report is the answer, not the outcome. A caller asking "is this study
sound?" gets a 200 and a report saying no, exactly as it gets a 200 and a
report saying yes; a non-2xx would mean "your request was wrong", which it was
not. `valid: false` is the field to branch on. 4xx is reserved for the request
itself being wrong: 404 for a study that does not exist, 422 for a body that is
not `{"sections": {...}}`.
"""

import asyncio
import uuid
from typing import Annotated, Any, Dict, Mapping, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..authoring.validate import KNOWN_GAPS, ValidationReport, validate_study
from .api_keys import require_scope
from .db import get_all_study_confs, get_study_id
from .deps import User, async_timeout, get_current_user

router = APIRouter()

# The work is one small database read plus pure pydantic. Generous rather than
# tight: a study with hundreds of strata is still milliseconds of validation,
# and the only thing that can actually hang is the database.
HANDLER_TIMEOUT_SECONDS = 30


class ValidateRequest(BaseModel):
    """The optional body.

    `sections` is keyed by conf type AS STORED — `data_sources`, not
    `data-sources` — because that is what a caller reading `GET /confs` back
    already holds, and what `validate_study` takes.
    """

    sections: Dict[str, Any] = Field(default_factory=dict)


class ValidateResponse(BaseModel):
    data: ValidationReport
    # Echoed on every response rather than documented only in prose, so a
    # client can show the caller what the verdict did NOT cover. The
    # Meta-dependent half of validation is out of scope by design (§10).
    known_gaps: list[str] = list(KNOWN_GAPS)


def overlay(stored: Mapping[str, Any], proposed: Mapping[str, Any]) -> Dict[str, Any]:
    """Stored sections with `proposed` replacing them, section by section.

    Whole-section replacement, never a deep merge, because that is exactly what
    a write does: `study_confs` is append-only and a POST stores one complete
    section, so the read-back is the last row for that conf type
    (`documentation/agent-api.md` §1.1). A deep merge here would validate a
    study that no sequence of writes could produce.

    An explicit `null` removes the section, so a caller can ask "what breaks if
    I have not written this yet?" — `validate_study` treats absent and null
    identically.
    """
    return {**dict(stored), **dict(proposed)}


CurrentUser = Annotated[User, Depends(get_current_user)]

# Belt and braces with `scope_enforcement_middleware`, exactly as in `meta.py`:
# the middleware is the fail-closed half and this puts the requirement in the
# route signature where a reader of this file can see it.
RequireStudiesRead = Annotated[None, Depends(require_scope("studies:read"))]


@router.post("/{org_id}/studies/{slug}/validate")
@async_timeout(HANDLER_TIMEOUT_SECONDS)
async def validate_study_endpoint(
    org_id: str,
    slug: str,
    user: CurrentUser,
    body: Optional[ValidateRequest] = None,
    _: RequireStudiesRead = None,
):
    """Validate the study's stored confs, optionally overlaid by proposed ones.

    With no body: validate what is stored. With `{"sections": {...}}`: validate
    the stored sections with those replaced, so an agent can check a change
    *before* writing it — which is the whole reason this is worth having, given
    that `study_confs` is append-only and a bad write cannot be taken back, only
    superseded.

    200 in both the valid and the invalid case. 404 for a study the caller
    cannot see.
    """
    proposed = body.sections if body is not None else {}

    def _work():
        # `orgs_lookup.org_id` is UUID, so an unparseable id would blow up in
        # the driver as a 500. Same treatment as `studies.py` and `meta.py`: a
        # malformed org id is definitionally not one the caller belongs to.
        try:
            uuid.UUID(org_id)
        except ValueError:
            raise HTTPException(
                status_code=404, detail=f"Organization not found: {org_id}"
            )

        # Raises 404 itself, and joins through orgs_lookup on the caller, so a
        # study in someone else's org is indistinguishable from one that does
        # not exist. Called for that check even though the confs come from
        # `get_all_study_confs`, which returns an empty dict rather than
        # raising — without it, validating a nonexistent study would happily
        # report "every section is missing".
        get_study_id(user.user_id, org_id, slug)

        stored = get_all_study_confs(user.user_id, org_id, slug)
        report = validate_study(overlay(stored, proposed))
        return {"data": report, "known_gaps": list(KNOWN_GAPS)}

    # Blocking psycopg in an `async def` handler would pin the event loop for
    # the whole request; `meta.py` established this pattern for the same hazard
    # and the reasoning is in its module docstring.
    return await asyncio.to_thread(_work)
