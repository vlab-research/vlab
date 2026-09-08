# MCP full coverage: everything the dashboard can do, over MCP

**Status:** Phases A and B implemented 2026-09-08 and shipped as **adopt
v0.1.92** — Phase A on `feature/mcp-observability-tools` (all seven tools, both
transports, seven `vlab` commands, six new `VlabClient` methods plus
`ad_attributions_csv`, and the three guards extended to cover them), Phase B on
`feature/strata-progress` rebased onto it (the `strata-progress` route and its
tool, twenty-six tools in all).

**Phase C implemented 2026-09-08 on `feature/mcp-accounts`, adopt v0.1.93**:
three `/users/accounts` routes and four tools, thirty in all. It is NOT merged
on the strength of the code alone — C2 stores a third-party secret that passed
through an agent's context, and that is the researcher's call. See §2 Phase C.

0.1.91 is SKIPPED, not missing: another session tagged that version at a
different commit while these branches were being written, so the code here has
never shipped under it and reusing the number would make the tag ambiguous.

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
| Participants-per-segment table: %desired / %current / %expected, expected participants, **budget**, **price per participant** per stratum; "Expected Participants" card | **Go only** (`GET /{org}/studies/{slug}/segments-progress`, reads `adopt_reports` `FACEBOOK_ADOPT`) | `strata_progress` | ~~**B1**~~ **closed** 2026-09-08 by `GET /{org}/studies/{slug}/strata-progress` |
| Study name by slug | Go `GET /{org}/studies/{slug}` | `list_studies` carries name and slug | none worth a tool |
| Connected accounts: list, add (Typeform, Fly, Alchemer, Qualtrics, generic api_key), update, delete | **Go only** (`/accounts`, user-scoped, returns raw secrets to the browser) | `list_accounts`, `create_account`, `delete_account` (secrets stripped everywhere); `meta_credentials` unchanged | ~~**C1**/**C2**/**C3**~~ closed 2026-09-08, except that `facebook` is not creatable |
| Create an API key | conf `POST /users/api-key` (then stored as an account via Go) | `list_api_keys`, `revoke_api_key`, `create_api_key` | ~~**C4**~~ closed 2026-09-08 |
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
  server allows five minutes. The window is
  `Recruitment.get_inference_window(now)` — `start_date`..`end_date` for
  `simple` and `destination`, and the CURRENT WAVE only for
  `pipeline_experiment` (`study_conf.py`). Not `general.opt_window`, which is
  the recruitment-data lookback for the budget arithmetic and lives on
  `general`, not `recruitment`.
- `recruitment_stats`: per-stratum dict; 404 when the study has never had a
  plan run, because respondent counts come from the latest `FACEBOOK_ADOPT`
  report. **Nothing in it is live.** `spend`, `reach`, `unique_clicks` and
  `impressions` are summed over all time from `recruitment_data_events`, which
  the `adopt-recruitment-data` cron writes every FOUR HOURS
  (`devops/values/toixo-prod.yaml`); the route makes no Meta call at all
  (`recruitment_data.calculate_stat_sql`). Calling the tool refreshes neither
  half, and `plan_study` refreshes only the respondent half.
- `respondents_over_time`: hourly buckets, cumulative WITHIN the inference
  window and across CURRENTLY-configured strata only — a respondent attributed
  to a since-renamed stratum is dropped — and anchored to the first and last
  interaction in the data rather than to the configured dates
  (`malaria.calculate_respondents_over_time_report`).
- `cost_over_time`: `cumulativeSpend` is ad spend PLUS incentives
  (`newRespondents * incentive_per_respondent`), `dailySpend` is ad spend
  alone, and `marginalCost` is `(dailySpend + incentives) / newRespondents`;
  days on which nothing changed are omitted, so the points are not consecutive
  days (`cost_over_time.py`).
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

### Phase B: the optimizer's per-stratum view — IMPLEMENTED 2026-09-08

Shipped on `feature/strata-progress`, rebased onto Phase A and released with it
as adopt v0.1.92. Route `server/strata_progress.py`, SQL
`campaign_queries.get_adopt_reports`, client `VlabClient.strata_progress`,
backend `InProcessBackend.strata_progress`, CLI `vlab strata-progress`, tool
`strata_progress`, reference `documentation/agent-api.md` §2.7. Tests:
`server/test_strata_progress.py` (the route), plus cases in `test_api_keys.py`,
`test_mcp_server.py`, `sdk/test_mcp_tools.py`, `sdk/test_client.py` and
`sdk/test_cli.py`.

Deviations from what is written below, all deliberate:

1. **404, not "the same text as `recruitment-stats` uses" verbatim.** The
   sentence is `get_latest_adopt_report`'s, with the SLUG substituted for the
   study id — an agent is never handed an id, so naming one in an error tells
   it nothing it can act on. `get_latest_adopt_report` itself is untouched.
2. **`percentage_deviation_from_goal` is computed, and on raw values.** Go
   rounds `desired` and `current` to two places and subtracts the rounded pair.
   That is a display decision; rounding here would mean the caller cannot
   recover the real number. Everything else is the report's own float.
3. **No `desired_participants`.** Go declares it as a nullable field and reads
   it if present. `budget.py`'s `report_facts` is the exhaustive list of what
   `make_report` writes and it has never contained that key, so the field would
   always be null. Recorded as a comment in `strata_progress.py`.
4. **A missing fact is a model default, not a 500**, with one warning logged per
   report rather than per stratum. Reports are JSONB written by whatever
   `budget.py` was deployed at the time; `efficiency_weight` and the
   counterfactuals postdate the earliest rows.
5. **The route is its own module** rather than another block in `server.py`,
   following `studies.py` / `validate.py` / `meta.py`. Its whole shape is an
   argument with the Go route it replaces, and that argument is a long docstring
   nobody should have to scroll past to reach the conf routes.
6. **`history` is bounded twice** — `Query(ge=1, le=200)` and an explicit check
   in the handler — because `InProcessBackend` calls the handler directly and
   the annotation enforces nothing there. Same pattern, and the same comment, as
   `list_studies_endpoint`.

Review fixes, 2026-09-08 (second commit on the branch):

7. **`_valid_org_or_404` before `get_study_id`.** A malformed `org_id` reached
   psycopg as a UUID comparison and came back a 500, where a non-member gets a
   404; the two have to be indistinguishable or the route is an oracle for which
   org UUIDs exist.
8. **The three `*_percentage` facts are FRACTIONS, 0..1** (`_normalize_values`
   is `v / sum`), and `current_budget` is `budget_lookup` — the allocation over
   the REST OF THE RECRUITMENT PERIOD, not a daily budget: the ad set's daily
   budget is `spend_for_day` of it (divided by days left and by destination
   arms, floored to the cent, zeroed below `min_budget`), so a non-zero
   allocation here can still be a paused ad set. And
   `current_price_per_participant` is `estimate_price`, a Gamma-Poisson
   posterior shrunk toward a prior of 2 + `incentive_per_respondent`, not a
   measurement. The first draft of the descriptions got all three wrong; they
   are the product surface, so this was the most expensive of the review's
   findings. The CLI's column heads lost their `%` accordingly, and it still
   multiplies nothing.
9. **A fact present but JSON-null defaults too**, not just an absent one. A
   stored `null` would otherwise 422 out of the model and reach the caller as a
   500 on a row nobody can fix.
10. **The missing-fact warning is the UNION of what each stratum lacks**, not
    the intersection, so a partially written report is reported. The two
    counterfactuals are excluded from that check — `budget.py` writes them only
    when a constraint binds, so including them would fire the warning on almost
    every healthy report, which is how a warning stops being read. Still one log
    line per report.

Original brief, unchanged:

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

### Phase C: connected accounts and key minting — IMPLEMENTED 2026-09-08

Branch `feature/mcp-accounts`. **Still needs the researcher's yes before it
merges**, for the reason at the bottom of this section: C2 stores a
third-party secret that passed through an agent's context.

What shipped:

- **C1** `GET /users/accounts[?auth_type=]` → `list_accounts(auth_type=None)`,
  `auth:read`. Every connected-account row of the caller's: `name`,
  `auth_type`, `created`, **never the secret**. Sorted `(auth_type, name)`.
  `meta_credentials` stays as it was — org-addressed, `meta:read`, the Meta
  proxy's own — and this is the same question asked of every provider under
  `auth:read`.
- **C2** `POST /users/accounts` → `create_account(name, auth_type,
  credentials)`, `auth:write`, 201. The Go upsert, in ONE transaction.
- **C3** `DELETE /users/accounts/{auth_type}/{name}` →
  `delete_account(auth_type, name)`, `auth:write`, 204/404.
- **C4** `create_api_key(name, scopes=None, expires_in_days=None)`,
  `auth:write`, on the EXISTING `POST /users/api-key`. No new route.

Plus `VlabClient.list_accounts` / `create_account` / `delete_account` /
`create_api_key`, `InProcessBackend` twins, and `vlab accounts list|add|delete`
and `vlab keys create`. New module `adopt/adopt/server/accounts.py`; SQL in
`server/db.py` beside `list_facebook_credentials`. Contract:
`documentation/agent-api.md` §2.7, §6b, §8 (2026-09-08).

#### Deviations from the plan above, and why

1. **C3's path is `/{auth_type}/{name}`, not `/{name}`.** The plan's shape
   cannot address a row: `unique_entity_key_per_user` is on
   `(user_id, entity, key)`, so `main` may exist under both `typeform` and
   `fly` and a name alone is ambiguous. The dashboard's Go route takes both in
   a DELETE *body*; a path is the same information somewhere a DELETE can
   legitimately carry it.

2. **`list_accounts` returns no "entity/identifier fields" for most types**,
   because there are none: every field of every credential shape IS the secret
   (`typeform.key`, `fly`/`qualtrics.api_key`, `alchemer`'s two, Facebook's
   `access_token`). The stripping is an ALLOWLIST — a provider added later is
   stripped bare until somebody widens it deliberately. The one exception is
   an `api_key` account's `details.id`, the minted key's `jti`, which
   `list_api_keys` already publishes and `revoke_api_key` takes.

   Facebook rows deliberately carry nothing extra either, so this and
   `GET /{org}/meta/credentials` describe a Facebook credential identically.
   `details.expires_in` is non-secret but is a duration from an issue time the
   row does not independently record, so publishing it would read as an expiry
   and not be one.

3. **vlab's own API-token rows are excluded from the listing**, and from the
   filter. They live in the same table (`api_token`, `api_token_revoked`) and
   the Go route lists them, because it filters on nothing. Listing them here
   would report one key twice under two shapes and offer a DELETE that looks
   like revocation and is not. `DELETE /users/accounts/api_token/<name>` is a
   400 pointing at `DELETE /users/api-keys/{id}` rather than a 404.

4. **`facebook` and `api_key` are 400s at create**, as the brief asked, with
   the alternative named in the message. Both remain listable and deletable:
   the dashboard allows deleting a Facebook account, and refusing here would
   diverge for no gain — the cost (a study whose `general.credentials_key`
   names it stops being able to reconcile) is stated in the tool and CLI
   descriptions instead.

5. **The upsert is one transaction, where Go's is two loose statements.**
   `db.upsert_account` opens one connection and lets psycopg's context manager
   commit both or neither, so a failure between the DELETE and the INSERT can
   no longer leave a user with no credential under a name a study still points
   at. `ON CONFLICT ... DO UPDATE` was rejected because it would preserve the
   original `created`, which is the field that distinguishes a re-connected
   credential from a stale one.

6. **A `ForeignKeyViolation` becomes a 409, not a 500.**
   `studies.credentials_key_exists` still references `credentials`, and though
   the modern create path leaves `studies.credentials_key` NULL, a legacy row
   written by `create_campaign_for_user` may not. Go answers an opaque 400.

#### The attenuation design for C4, which is the security-critical part

`create_api_key` is the one handler whose authorization depends on something
`deps.User` does not carry: the SCOPES of the key doing the minting. Over HTTP
it gets them by calling `scopes_for_token` on the `HTTPAuthorizationCredentials`
FastAPI injected, then `scopes_allow(..., "auth:write")` and
`can_grant_scopes`.

`InProcessBackend` had only the `User`. Two ways to give it what it needs:
refactor the handler to accept pre-computed scopes, or carry the caller's raw
bearer token and hand it back. **The token was chosen**, because it makes the
in-process path run the handler's own code rather than a second copy of the
rule, and a second copy of exactly this rule is how a transport quietly becomes
a privilege-escalation route. `MCPEndpoint` already has the token in hand — it
passes it to `scopes_for_token` for the per-tool authorizer — the token lives
no longer than the request, and the lookup is cached, so the second call is a
cache hit rather than a second verification.

`InProcessBackend(user, token=None)` keeps `token` optional so every other
method works without one, and `create_api_key` fails CLOSED with a 403 when it
is absent: assuming "unrestricted" there would be the escalation.

Pinned by `server/test_mcp_server.py`: a `studies:read` key is denied
`create_api_key` by `TOOL_SCOPES` naming `auth:write`; an
`auth:write`+`studies:read` key gets the route's own attenuation error when it
asks for `optimize:write`; omitting `scopes` from a scoped key is refused
because absent means full access; a minted child works immediately and no
further than its scopes; and `MCPEndpoint` is asserted to hand the backend the
caller's token, so a regression in the wiring names itself.

#### The open decision, unchanged

**C2 sends a third-party secret through an agent's context and stores it.** It
is in the transcript, in any log of the session, and in the request to vlab.
The dashboard sends the same secret through a browser, so this is not a new
class of exposure — but it is a new place for it, and it is the researcher's
call, not the implementation's. The mitigations that are in the code:

* the `create_account` tool description says so in as many words, and tells an
  agent to prefer having the human do it;
* `vlab accounts add` reads the secret from a file or stdin and has **no flag
  that takes one on a command line** — a token in argv is in the shell history
  and in `ps` for every user on the machine;
* nothing ever reads a secret back out, so an agent cannot exfiltrate one it
  did not already hold.

If the answer is no, **C1, C3 and C4 stand on their own**: listing closes the
runbook gap "which `credentials_key` do I use", deleting closes rotation, and
minting closes sub-agent keys. Dropping C2 means deleting one route, one tool,
one client method and one CLI command; nothing else depends on it.

## 3. What stays out

- **Facebook connect.** Browser OAuth; `agent-api.md` §7 item 2.
- **Template campaigns over MCP.** `planning/mcp.md` §8, unchanged.
- **Client-side CSV downloads.** The recruitment-stats CSV is built in the
  browser from the JSON; an agent has the JSON.
- **The Go routes themselves.** Nothing here touches `api/`; the dashboard
  keeps using it. Retiring Go routes is `agent-study-authoring.md` §7.

## 4. Follow-ups this phase found and did not fix

Phase A was a wrapping exercise, so anything wrong on the far side of a route
was documented rather than changed: a tool that quietly corrected a field would
disagree with the dashboard showing the same study, which is worse than a
consistent oddity.

- **`recruitment_stats.cpm` is not cost per mille.** It is computed as
  `impressions / spend` — impressions per dollar, so bigger is cheaper
  (`recruitment_data.calculate_stat_sql`, the `AdPlatformRecruitmentStats`
  construction). Cost per mille would be `spend / impressions * 1000`, which is
  a different number and moves the other way. The dashboard's Recruitment
  Statistics table shows this figure under the label CPM, so the tool, the CLI
  and the client report it as-is and say what it is. Fixing it means either
  renaming the field (a dashboard change and a payload change) or changing the
  arithmetic (which would silently redefine a number researchers have been
  reading for a year). Neither belongs in a phase whose rule is "the tool
  returns what the route returns".
- **Nothing an API key can call refreshes the spend half.** `plan_study`
  refreshes the FACEBOOK_ADOPT report and the two time series; the spend rows
  come only from the four-hourly `adopt-recruitment-data` cron. An agent that
  wants current spend has to wait for it. Worth a route eventually; out of
  scope here.
