# Discovery: listing orgs and studies

**Status:** implemented, adopt v0.1.88. Branch `feature/list-studies`.

## The gap

`documentation/agent-api.md` §7 item 1 said it plainly: *"Discover its own
`org_id`. No API-key-reachable endpoint lists orgs."* Everything downstream of
that repeated it — the `create_study` MCP tool description ("Nothing an API key
can call lists orgs -- a human has to hand you the id"), `cli.parse_target`'s
error message, the §6.1 runbook's `export VLAB_ORG=0f1e...  # a human tells you
this`, and `adopt/README.md`'s study-file header comment.

So an agent holding a freshly-minted API key could do everything except find
out *what it could do it to*. It had to be handed a UUID out of band, and if it
was handed the wrong one the only feedback was a 404 that deliberately does not
distinguish "not yours" from "does not exist". Step zero of the runbook was a
human.

Two read-only routes close it.

## The routes

| Route | Scope | Returns |
|---|---|---|
| `GET /orgs` | `studies:read` | `{"data": [{id, name}]}` — orgs the caller belongs to, by name |
| `GET /{org_id}/studies` | `studies:read` | `{"data": [{id, name, slug, created}]}` — newest first |

`limit` (1–500, default 100) and `offset` (≥0) on the second.

### Why `studies:read` for `/orgs`, and not a new resource

An org is the *namespace* a study lives in: every study route on this service
is `/{org_id}/studies/...`, and the only thing `GET /orgs` tells you is which
of those prefixes will not 404. A key that may read an org's studies may know
the org exists. Inventing an `orgs` resource would mean every existing
`studies:read` key stops being able to complete the runbook — a scope widening
applied retroactively to keys already issued, which is exactly the mistake
`validate_study`'s docstring warns about ("so that the scope a key needs for
this tool never has to be WIDENED later").

`GET /{org_id}/studies` needed no classification work at all:
`required_scope`'s `area == "studies"` branch already computes
`tail = segments[3] if len(segments) > 3 else ""` and maps the empty tail to
`studies:{action}`. The route was classified before it existed. `/orgs` did
need a branch, beside the `/users` one, because it is the one path in this
service that is neither `/users/...` nor `/{org_id}/...`.

The `/orgs` branch is an EXACT match on a single segment, unlike the `meta` and
`users` branches which claim their whole subtree. `/orgs/{id}/members` is a
route somebody might plausibly add, it would not be a `studies:read` thing, and
`required_scope` returning `None` for it (→ denied for scoped keys) is the
direction that mistake should point.

## Access model, and the divergence from the Go dashboard API

The dashboard lists studies through the Go service
(`api/internal/storage/study.go` `GetStudies`), whose query is:

```sql
SELECT id, name, slug, created FROM studies
WHERE user_id = $3 OR org_id = $4
ORDER BY created DESC OFFSET $1 LIMIT $2
```

This service does **not** reproduce that, deliberately. Two halves, both wrong
here:

1. **`org_id = $4` with no membership check.** Go gets away with it because the
   org id comes from the dashboard's own session state, not from the caller. On
   this service the org id is a path segment supplied by whoever holds the key,
   so the Go query would let any authenticated key list any org's studies by
   guessing a UUID. Every other read on the conf service reaches a study
   through `JOIN orgs_lookup ol ON ol.org_id = s.org_id` (see `db.get_study_id`,
   `db.get_study_conf`), and this one does too.
2. **`user_id = $3` regardless of org.** It returns the caller's own studies
   from *other* orgs under the requested org's URL. Harmless in the dashboard,
   where the two sets almost always coincide; incoherent as an API whose whole
   addressing scheme is `/{org}/studies/{slug}`.

So: **studies in an org the caller is a member of**, whoever created them. That
is the same rule `POST /{org_id}/studies` enforces by construction (its
`INSERT … SELECT FROM orgs_lookup`) and the same rule the nine conf routes
enforce by join.

A consequence worth naming: studies with a NULL `org_id` — rows predating the
2023 organisation migration, and any row `create_campaign_for_user` wrote
(Appendix A.1's bug) — are invisible here, exactly as they are invisible to
every conf route. They are not "missing"; they are unreachable through this
service entirely, and a list that showed them would show studies nothing else
here can address.

### Why membership is a separate query

`create_study` gets its membership check for free: the INSERT selects from
`orgs_lookup`, so a non-member writes no rows and the route reads "not a
member" off an empty result. A SELECT cannot do that — an empty result means
"not a member" *or* "member of an empty org", and those need different answers
(404 vs `200 []`). So the route calls `db.user_in_org` first, which already
existed for exactly this reason on the Meta routes.

The window between the check and the list is real and does not matter: it is
two reads, both of data the caller was a member for at the moment they asked.

### 404, and why it is the same 404

A non-member, an unknown org and a malformed UUID all get
`404 "Organization not found: {org_id}"` — byte for byte what the create route
gives. Indistinguishable on purpose: distinguishing them turns `GET /{org}/studies`
into an oracle for which org UUIDs exist. The malformed-UUID case is also a
crash guard: `orgs_lookup.org_id` is `UUID`, so an unparseable value would
otherwise surface as a 500 from the driver.

## `created` is ISO 8601 here, and milliseconds on the create route

`POST /{org_id}/studies` answers `createdAt` as milliseconds since the epoch,
because it is a port of the Go handler and the dashboard's
`CreateStudyApiResponse` parses that number. Nothing consumes this list route
yet, so it is free to be readable: `created` is ISO 8601 with an explicit
`+00:00`.

The UTC is an assumption, and the same one the create route makes:
`studies.created` is `TIMESTAMP` without zone and comes back naive; Go scans it
into a UTC-naive `time.Time` and calls `UnixMilli()`. Pinning `timezone.utc` is
what reproduces the dashboard's number, so stamping the offset here is honest
rather than invented.

## Paging: `limit`/`offset`, not Go's cursor

The Go route takes `number` (default 20, max 100) and a base64url-encoded
`cursor` that decodes to… an integer offset
(`api/internal/helpers/pagination.go`). The encoding buys nothing — it is an
offset wearing a hat — and an agent would have to base64 its way through a
list. Plain `limit`/`offset`, with a higher default (100) because an agent
reading a list is not a UI painting a page.

## One implementation, every front door

Plan §7's row, applied: the route is the only place the query lives.
`VlabClient.list_orgs` / `list_studies` call it over HTTP; `vlab orgs` /
`vlab studies` call the client; the `list_orgs` / `list_studies` MCP tools call
the client (stdio) or the route handler (`POST /mcp`, via
`InProcessBackend`). No layer decides anything the layer below it does not.

The MCP tools take `limit`/`offset` too, which the brief for this change did
not ask for. Without them a tool that hits the default cap has no way past it,
and every `meta_*` tool already takes paging arguments — a discovery tool that
silently truncates is worse than one with two optional integers.

## Tests

- `server/test_studies.py` — member sees studies newest first and across
  creators, empty org is `200 []`, non-member 404, unknown org 404, malformed
  org 404, NULL-`org_id` studies invisible, limit/offset, `/orgs` lists only
  the caller's orgs.
- `server/test_api_keys.py` — `required_scope` for both paths; a
  `studies:read` key reaches both; a `meta:read` key is denied both with the
  scope named.
- `sdk/test_client.py` — call-through against the real app.
- `sdk/test_cli.py` — table and `--json` output for both commands.
- `sdk/test_mcp_tools.py` — call-through against a recording backend.
- `server/test_mcp_server.py` — `ROUTE_BACKED_TOOLS` entries (which is what
  pins tool scope == route scope), and a `list_studies` call over `POST /mcp`
  with a `studies:read` key against the real database.

## What this does not do

- **No `GET /{org_id}/studies/{slug}`.** `GET /confs` is the read an agent
  wants and the list gives the slug; a per-study metadata route would be a
  third way to learn a name.
- **No cross-org study search.** Two calls, and the org is the unit of access.
- **The Go route is untouched.** The dashboard keeps using it. Retiring it is
  the separate piece of work `agent-study-authoring.md` §7 books under
  "deprecate the Go endpoint".
