"""Study creation, and the two discovery reads, on the conf service.

Port of `POST /:org/studies` from the Go dashboard API
(`api/internal/server/handler/studies/create.go`), which is Auth0-only. This
service accepts either Auth0 or a vlab API key (`auth.verify_tokens`), so with
this endpoint an agent or a script holding an API key can create a study and
then configure it, instead of needing a human to click "new study" in the
dashboard first. That was the single hardest blocker in
planning/agent-study-authoring.md §3; the port is specified by Appendix A.1.

The Go handler is the spec, not `create_campaign_for_user`
(`adopt/campaign_queries.py:66`) — see the docstring on `db.create_study` for
the two bugs in that one. What the Go handler does, and this reproduces:

* validate the name in the *handler* (blank, and a 300 cap), not the database
* slug via `gosimple/slug`.`Make` — see `slugify.py`, which is a real port
* respond 201 `{"data": {id, name, slug, createdAt}}`, the shape
  `CreateStudyApiResponse` already expects (`dashboard/src/types/study.ts`),
  so the dashboard can be repointed here without a client change
* map a unique-constraint violation to 409 "The name is already in use."

THE TWO READS
-------------

`GET /orgs` and `GET /{org_id}/studies` are the discovery half, added later
(planning/list-orgs-studies.md). They live here rather than in `server.py`
because they are the same resource seen from one level up, and because
`required_scope` classifies both as `studies:read`.

They are ports too -- of `GetUserOrgIDs` and `GetStudies` on the Go service --
but only in the sense of answering the same questions. `GetStudies`'s access
predicate is `user_id = $3 OR org_id = $4`, and this service does not reproduce
it; `db.list_studies` says why at length.
"""

import logging
import uuid
from datetime import timezone
from typing import Annotated, List, Optional

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from .db import create_study, list_orgs, list_studies, user_in_org
from .deps import User, get_current_user
from .slugify import slugify

router = APIRouter()

# Go: `len(req.StudyName) > 300`. `len` on a Go string counts BYTES, so the
# dashboard's real limit is 300 UTF-8 bytes and a 300-character Cyrillic name
# is already rejected there. We count bytes for the same reason we port the
# slug exactly: the two services must accept and reject the same names. The
# user-facing wording is Go's, verbatim, so the dashboard's copy is unchanged.
MAX_NAME_BYTES = 300


class CreateStudyRequest(BaseModel):
    name: str


class StudyResource(BaseModel):
    id: str
    name: str
    slug: str
    # Milliseconds since the epoch, matching Go's `created.UnixMilli()`.
    createdAt: int


class CreateStudyResponse(BaseModel):
    data: StudyResource


class OrgResource(BaseModel):
    id: str
    # Nullable in the schema (`orgs.name string UNIQUE`, no NOT NULL), and Go
    # scans it into a `sql.NullString` for that reason. Promising a `str` here
    # would turn one unnamed row into a 500 on the whole list.
    name: Optional[str] = None


class ListOrgsResponse(BaseModel):
    data: List[OrgResource]


class StudyListItem(BaseModel):
    id: str
    name: str
    slug: str
    # ISO 8601 with an explicit offset, NOT the `createdAt` milliseconds the
    # create route above answers with. That one is milliseconds because it is a
    # port of the Go handler and the dashboard's `CreateStudyApiResponse`
    # parses the number; nothing consumes this list route, so it is free to be
    # legible to the agent and the human who are its only readers.
    created: str


class ListStudiesResponse(BaseModel):
    data: List[StudyListItem]


# The default is a list length, not a UI page: an agent reading its orgs's
# studies wants them all, and 100 is past every real org. The ceiling exists so
# that `?limit=1000000` is a 422 rather than a query.
DEFAULT_STUDIES_LIMIT = 100
MAX_STUDIES_LIMIT = 500


def _valid_org_or_404(org_id: str) -> None:
    """Reject an org id the database cannot even compare.

    `orgs_lookup.org_id` is UUID, so a malformed value would otherwise blow up
    in the driver as a 500. An unparseable org id is definitionally not an org
    the caller belongs to, so it gets the same answer as one they simply are
    not in -- and the same answer an org that does not exist gets. All three
    are indistinguishable on purpose: telling them apart would make these
    routes an oracle for which org UUIDs exist.
    """
    try:
        uuid.UUID(org_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Organization not found: {org_id}")


def _validate_name(name: str) -> str:
    """Reproduce `parseRequest`, and return the slug.

    Note that the *name* is stored untrimmed, exactly as Go stores
    `req.StudyName`; only the blank check and the slug see a trimmed version.
    This matters because `unique_name` is on the raw column, so "foo" and
    " foo " are two different names but collide on `unique_slug`.
    """
    if not name.strip():
        raise HTTPException(status_code=400, detail="The name cannot be empty.")

    if len(name.encode("utf8")) > MAX_NAME_BYTES:
        raise HTTPException(
            status_code=400,
            detail="The name cannot be larger than 300 characters.",
        )

    slug = slugify(name)

    # Deliberate divergence from Go, which does not check this. A name whose
    # every character transliterates to nothing — emoji, or any codepoint
    # above the BMP — slugs to "". Go happily writes that row, and the result
    # is a study that no URL can address: every conf route is
    # /{org}/studies/{slug}/..., and an empty path segment matches nothing.
    # Rejecting is strictly narrower than Go, so it can never hand out a
    # *different* slug than the dashboard would for a name Go accepts; it only
    # refuses to create a study that would be dead on arrival.
    if not slug:
        raise HTTPException(
            status_code=400,
            detail=(
                "The name must contain at least one letter or number "
                "that can be used in a URL."
            ),
        )

    return slug


@router.post("/{org_id}/studies", status_code=201, response_model=CreateStudyResponse)
async def create_study_endpoint(
    org_id: str,
    body: CreateStudyRequest,
    user: Annotated[User, Depends(get_current_user)],
):
    slug = _validate_name(body.name)

    _valid_org_or_404(org_id)

    try:
        study = create_study(user.user_id, org_id, body.name, slug)
    except psycopg.errors.UniqueViolation as e:
        # Both constraints are per-(user_id, ...), not per-org. Go returns one
        # message for both; we keep that sentence first so any client matching
        # on it still works, and add the slug for the case that is otherwise
        # baffling — a *different* name that slugifies onto a taken slug.
        constraint = e.diag.constraint_name
        if constraint == "unique_slug":
            raise HTTPException(
                status_code=409,
                detail=(
                    f'The name is already in use: it produces the slug "{slug}",'
                    " which belongs to another of your studies."
                ),
            )
        if constraint == "unique_name":
            raise HTTPException(status_code=409, detail="The name is already in use.")
        # Some other unique constraint we do not know about. Do not swallow it
        # as a 409 — that would tell the caller to rename, which will not help.
        logging.error("Unexpected unique violation creating study: %s", e)
        raise

    if study is None:
        # Not a member of the org. 404 rather than 403, consistent with every
        # other lookup in db.py: a caller outside the org learns nothing about
        # whether it exists.
        raise HTTPException(status_code=404, detail=f"Organization not found: {org_id}")

    # `studies.created` is TIMESTAMP (no zone) and comes back naive. Go scans
    # it into a time.Time that is likewise UTC-naive and calls UnixMilli(), so
    # pinning UTC here is what reproduces the dashboard's number.
    created_ms = int(study["created"].replace(tzinfo=timezone.utc).timestamp() * 1000)

    return {
        "data": {
            "id": str(study["id"]),
            "name": study["name"],
            "slug": study["slug"],
            "createdAt": created_ms,
        }
    }


@router.get("/orgs", response_model=ListOrgsResponse)
async def list_orgs_endpoint(user: Annotated[User, Depends(get_current_user)]):
    """The caller's organisations. Step zero of the runbook.

    Until this existed, an agent holding an API key could do everything to a
    study except find out which org to do it in: the id had to be handed over
    out of band, and a wrong one produced a 404 that deliberately says nothing.
    See planning/list-orgs-studies.md.

    Scoped `studies:read`, not a new `orgs` resource. An org is the namespace a
    study lives in -- every study route here is `/{org_id}/studies/...` -- and
    the only thing this route reveals is which of those prefixes will not 404.
    A new resource would also have RETROACTIVELY widened what a key needs to
    complete the runbook, breaking every `studies:read` key already issued.

    Note that this path does not begin with an org id, which is why
    `api_keys.required_scope` needs a branch for it beside the `/users` one.
    """
    orgs = list_orgs(user.user_id)
    return {"data": [{"id": str(o["id"]), "name": o["name"]} for o in orgs]}


@router.get("/{org_id}/studies", response_model=ListStudiesResponse)
async def list_studies_endpoint(
    org_id: str,
    user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(DEFAULT_STUDIES_LIMIT, ge=1, le=MAX_STUDIES_LIMIT),
    offset: int = Query(0, ge=0),
):
    """Studies in an org the caller belongs to, newest first.

    `limit`/`offset` rather than the Go route's `number` and base64url
    `cursor`: that cursor decodes to an integer offset
    (`api/internal/helpers/pagination.go`), so it is an offset wearing a hat,
    and an agent should not have to base64 its way through a list.

    MEMBERSHIP IS CHECKED SEPARATELY, and has to be. The create route gets its
    check for free -- a non-member's `INSERT ... SELECT FROM orgs_lookup`
    writes no rows, so an empty result IS "not a member". A SELECT has no such
    luck: no rows means "not a member" or "member of an org with no studies",
    and those are a 404 and a `200 []`. Hence `user_in_org` first.
    """
    # Belt and braces with the `Query(ge=..., le=...)` above, which only runs
    # when FastAPI parses a query string. `POST /mcp` calls this handler
    # DIRECTLY (`server/mcp_server.InProcessBackend`), so on that front door
    # the annotations enforce nothing and a negative offset would reach
    # psycopg and come back as a 500. Same 422 either way.
    if not 1 <= limit <= MAX_STUDIES_LIMIT or offset < 0:
        raise HTTPException(
            status_code=422,
            detail=(
                f"limit must be between 1 and {MAX_STUDIES_LIMIT} and offset "
                f"must not be negative; got limit={limit}, offset={offset}."
            ),
        )

    _valid_org_or_404(org_id)

    if not user_in_org(user.user_id, org_id):
        # The same sentence, byte for byte, that the create route gives for a
        # non-member. See `_valid_org_or_404`.
        raise HTTPException(status_code=404, detail=f"Organization not found: {org_id}")

    studies = list_studies(user.user_id, org_id, limit, offset)

    return {
        "data": [
            {
                "id": str(s["id"]),
                "name": s["name"],
                "slug": s["slug"],
                # `studies.created` is TIMESTAMP (no zone) and comes back
                # naive. The create route pins UTC to reproduce Go's
                # `UnixMilli()`; the same assumption, stamped rather than
                # implied, is what makes this string unambiguous.
                "created": s["created"].replace(tzinfo=timezone.utc).isoformat(),
            }
            for s in studies
        ]
    }
