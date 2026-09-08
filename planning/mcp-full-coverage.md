# MCP full coverage: everything the dashboard can do, over MCP

**Status:** Phase A implemented 2026-09-08 on branch
`feature/mcp-observability-tools`, adopt v0.1.91 — all seven tools, both
transports, seven `vlab` commands, six new `VlabClient` methods (plus
`ad_attributions_csv`), and the three guards extended to cover them. Phases B
and C are not started.

**Goal, in the researcher's words:** "full coverage so that everything we can
do in the user interface, we can do over MCP." This document is the gap
matrix between the dashboard and the 18 tools that shipped in adopt v0.1.89,
and the order the gaps close in. It extends `planning/mcp.md`, which is the
design record for the transport and the add-a-tool recipe; nothing here
changes that design.

## 1. The matrix

Built 2026-09-08 from a sweep of `dashboard/src` (every path string in
`helpers/api.ts` and every hook that uses it), of the Go API's route table
(`api/internal/server/server.go`, 12 routes) and of the conf service
(`adopt/adopt/server`, classified by `api_keys.required_scope`). The dashboard
talks to three hosts: the Go API, the conf service, and Meta's Graph API
directly from the browser.

| Dashboard capability | Where the dashboard gets it | MCP today | Gap |
|---|---|---|---|
| List studies, create study | Go (`/{org}/studies`) | `list_studies`, `create_study` | none |
| Read all conf sections | conf `GET .../confs` | `pull_study` | none |
| Save each of the 9 conf sections | conf `POST .../confs/{type}` | `push_study` (+ `validate_study`, `diff_study`) | none |
| Initialize: copy confs from another study | conf `POST .../copy-from` | `copy_study_from` | ~~A7~~ closed |
| Regenerate strata, extract targeting from an ad set | client-side | `compile_strata`, `extract_targeting` | none |
| Ad accounts, campaigns, ad sets, ads (with creatives) | Graph, from the browser | `meta_*` proxies | none |
| Optimize (plan), run one instruction | conf `GET /optimize/{slug}`, `POST .../instruction` | `plan_study`, `apply_instruction` | none |
| Errors tab and the sidebar badge | conf `GET /optimize/{slug}/errors` | `study_errors` | ~~A1~~ closed |
| Current Data tab | conf `GET /optimize/{slug}/current-data` | `current_data` | ~~A2~~ closed |
| Ad Attributions tab (+ CSV) | conf `GET .../ad-attributions` | `ad_attributions` (+ `vlab ad-attributions --csv`) | ~~A3~~ closed |
| Recruitment Statistics table (spend, CPM, price per respondent, incentive and total cost, conversion) | conf `GET .../recruitment-stats` | `recruitment_stats` | ~~A4~~ closed |
| Participants-over-time chart, "Current Participants" card | conf `GET .../segments-progress` | `respondents_over_time` | ~~A5~~ closed |
| Total Spent, Avg Cost per Participant, spend and marginal-cost charts | conf `GET .../cost-over-time` | `cost_over_time` | ~~A6~~ closed |
| Participants-per-segment table: %desired / %current / %expected, expected participants, **budget**, **price per participant** per stratum; "Expected Participants" card | **Go only** (`GET /{org}/studies/{slug}/segments-progress`, reads `adopt_reports` `FACEBOOK_ADOPT`) | — | **B1**: no conf-service route exists |
| Study name by slug | Go `GET /{org}/studies/{slug}` | `list_studies` carries name and slug | none worth a tool |
| Connected accounts: list, add (Typeform, Fly, Alchemer, Qualtrics, generic api_key), update, delete | **Go only** (`/accounts`, user-scoped, returns raw secrets to the browser) | `meta_credentials` (Facebook only, secrets stripped) | **C1** list, **C2** create/update, **C3** delete: no conf-service routes |
| Create an API key | conf `POST /users/api-key` (then stored as an account via Go) | `list_api_keys`, `revoke_api_key` | **C4** |
| Connect a Facebook account | Facebook OAuth dialog + Go `POST /facebook/token` | — | **not closable**: the OAuth code exchange needs a browser and a human; documented in `agent-api.md` §7 item 2 |
| Log in | Auth0 | — | not applicable: an API key *is* the login |

Everything the dashboard reads on the study page is a time series or snapshot
the optimizer wrote to `adopt_reports` during a plan run, plus live Meta
insights for `recruitment-stats`. None of it is computed by the dashboard, so
none of it needs a client-side port: the tool returns what the route returns.

## 2. Phases

Each phase is one PR, reviewed independently before merge, released with
`scripts/release.sh` and a values bump, exactly as Phases 0–4 were. Every tool
follows the recipe in `planning/mcp.md` and is pinned by the same three
guards: `TOOL_SCOPES[tool] == required_scope(method, path)`
(`ROUTE_BACKED_TOOLS` in `server/test_mcp_server.py`), the description test,
and the stdio-vs-remote drift guard.

### Phase A: the seven tools whose routes already exist — **shipped**

Read-only unless marked. The rule from Phase 4 holds: **one implementation
per capability**. Tool → `VlabClient` method (stdio) or `InProcessBackend`
method calling the route handler (remote), and a `vlab` CLI command on the
same client method.

| Tool | Route | Scope | Client method | CLI |
|---|---|---|---|---|
| A1 `study_errors(org, slug)` | `GET /{org}/optimize/{slug}/errors` | `optimize:read` | `study_errors` (exists) | `vlab errors <org>/<slug>` |
| A2 `current_data(org, slug)` | `GET /{org}/optimize/{slug}/current-data` | `optimize:read` | `current_data` (new) | `vlab current-data <org>/<slug>` |
| A3 `ad_attributions(org, slug)` | `GET /{org}/studies/{slug}/ad-attributions` | `responses:read` | `ad_attributions` (new) | `vlab ad-attributions <org>/<slug>` (`--csv` writes the `.csv` route's body) |
| A4 `recruitment_stats(org, slug)` | `GET /{org}/studies/{slug}/recruitment-stats` | `stats:read` | `recruitment_stats` (new) | `vlab stats <org>/<slug>` |
| A5 `respondents_over_time(org, slug)` | `GET /{org}/studies/{slug}/segments-progress` | `stats:read` | `respondents_over_time` (new) | `vlab respondents <org>/<slug>` |
| A6 `cost_over_time(org, slug)` | `GET /{org}/studies/{slug}/cost-over-time` | `stats:read` | `cost_over_time` (new) | `vlab costs <org>/<slug>` |
| A7 `copy_study_from(org, slug, source_slug)` — **writes** | `POST /{org}/studies/{slug}/copy-from` | `studies:write` | `copy_from` (exists) | `vlab copy-from <org>/<slug> <source_slug>` |

Names: the tool is named for what the researcher sees, not for the route.
`segments-progress` on the conf service is the respondents-over-time series
and nothing else (the Go route of the same path is a different thing, see
B1), so the tool says so.

Description content that the tests will enforce and that the agent needs:

- `study_errors`: derived from `study_run_events`, latest event per
  fingerprint, only errors and warnings seen in the last 90 minutes; an empty
  list means "nothing is currently re-emitting", not "healthy". Today only
  swoosh (data extraction) writes events; adopt writes none, so ad-building
  failures do not appear here (`agent-api.md` §2.3).
- `current_data`: one row per respondent per variable inside the study's
  inference window; this is the data the optimizer sees. Can be large; the
  server allows five minutes.
- `recruitment_stats`: per-stratum dict; 404 when the study has never had a
  plan run, because respondent counts come from the latest `FACEBOOK_ADOPT`
  report. Spend and clicks are live Meta insights summed over all time.
- `respondents_over_time`, `cost_over_time`: read the latest pre-computed
  report; empty until the first plan run. A plan run (`plan_study`) is what
  refreshes them, and it is not side-effect free.
- `copy_study_from`: copies every section except `general`, appending new
  rows; nothing is deleted, and the copy supersedes whatever the target had.

**What Phase A actually shipped, and the two things worth knowing.**

`study_errors` on `VlabClient` already existed and was WRONG in a way nothing
called: the errors route wraps its payload under `errors`, not `data`, so
`_data` handed back the envelope where every neighbouring method returns the
payload. It now unwraps, and a test pins it. That is the only pre-existing
behaviour this phase changed, and no route moved.

`ad-attributions` is two routes, and the CSV one answers `text/csv`. `request`
raises `TransportError` for a body that is not JSON — correctly, everywhere
else — so `VlabClient.request_text` was split out alongside it over a shared
`_send`. `--csv` therefore writes the SERVER's rendering rather than the CLI's
rendering of the JSON, which is what makes "the table and the file cannot
disagree" true rather than aspirational. The tool deliberately exposes only the
JSON: an MCP tool returning a CSV blob is a worse table than a table.

The in-process backend calls `model_dump(mode="json")` on every pydantic
response here, not `model_dump()`. The HTTP path serialises `last_seen` and
`first_seen` through pydantic's JSON serializer, and a plain dump would hand a
tool `datetime` objects on one transport and ISO strings on the other — a
divergence no single-transport test could see, and exactly what the drift guard
exists for.

### Phase B: the optimizer's per-stratum view

B1 is the "optimization results and prices" question. The Go route explodes
every `FACEBOOK_ADOPT` report ever written into per-stratum rows with
`currentBudget`, `desiredPercentage`, `currentPercentage`,
`expectedPercentage`, `expectedParticipants`, `currentParticipants`,
`currentPricePerParticipant`. The report itself (`budget.py`,
`report_facts`) also carries `total_spent`, `lifetime_spent`,
`efficiency_weight` and, when present, the two counterfactuals; Go drops
those.

New conf-service route: **`GET /{org_id}/studies/{slug}/strata-progress`**,
`stats:read` (add to the `stats` tail tuple in `required_scope`). Returns the
latest report by default, exploded per stratum with every fact the report
holds, in snake_case, plus the report's `created` timestamp. `?history=N`
returns the last N reports newest first (bounded, say 1–200) so an agent can
see how budget moved. 404 when no report exists, same text as
`recruitment-stats` uses. Ownership through `get_study_id`, like every study
read. Tool `strata_progress(org, slug, history=1)`, client method, `vlab
strata-progress`.

Not the Go path name: the conf service already serves `segments-progress`
with a different shape, and two routes with one name and two payloads is the
trap the dashboard already lives with.

### Phase C: connected accounts and key minting (needs a decision)

These are writes of secrets, and the researcher should say yes before they
ship. Built as a PR, not merged until they do.

- **C1** `GET /users/accounts` → `list_accounts()`: every credential row of
  the caller's, `name`, `auth_type`, `created`, entity/identifier fields,
  **never the secret**. `auth:read`. This is `meta_credentials` widened to all
  providers; the Meta one stays because it is org-addressed and the Meta
  proxy's own.
- **C2** `POST /users/accounts` → `create_account(name, auth_type,
  credentials)`: the Go upsert, on the conf service, `auth:write`. The value
  is that a `data-sources` section needs a `credentials_key`, and today an
  agent cannot make one.
- **C3** `DELETE /users/accounts/{name}` → `delete_account`: `auth:write`.
- **C4** `create_api_key(name, scopes, expires_in_days)` on the existing
  `POST /users/api-key`, `auth:write`, attenuated by the route (a child key
  cannot exceed its parent). The token is returned once and the tool says so.

Open question for the researcher: C2 sends a third-party secret through an
agent's context and stores it. The dashboard does the same through a browser.
If that is unwelcome, C1 and C4 alone still close the runbook gap "which
`credentials_key` do I use".

## 3. What stays out

- **Facebook connect.** Browser OAuth; `agent-api.md` §7 item 2.
- **Template campaigns over MCP.** `planning/mcp.md` §8, unchanged.
- **Client-side CSV downloads.** The recruitment-stats CSV is built in the
  browser from the JSON; an agent has the JSON.
- **The Go routes themselves.** Nothing here touches `api/`; the dashboard
  keeps using it. Retiring Go routes is `agent-study-authoring.md` §7.
