"""Study creation on the conf service.

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
"""

import logging
import uuid
from datetime import timezone
from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .db import create_study
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

    # `orgs_lookup.org_id` is UUID, so a malformed org id would otherwise blow
    # up in the driver as a 500. An unparseable org id is definitionally not
    # an org the caller belongs to, so it gets the same answer as one they
    # simply are not in.
    try:
        uuid.UUID(org_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Organization not found: {org_id}")

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
