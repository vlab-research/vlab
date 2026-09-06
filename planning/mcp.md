# Phase 4: the MCP shim

Implemented 2026-09-06 on `feature/mcp`, merged in #271 and in production as adopt v0.1.87 the same day. Post-deploy checks: all four uvicorn workers started the session manager; `GET`/`DELETE /mcp` 405, unauthenticated `POST /mcp` 403, bad token 401; `/openapi.json` unchanged; cronjobs on v0.1.87. This is the phase-notes file for
Phase 4 of `planning/agent-study-authoring.md` §16, written in the discipline
of `planning/vlab-sdk.md`: what shipped, the decisions with their reasons,
where the brief was wrong, and what is deliberately not done or still open.

§16 was written the same day and is the brief. Where this disagrees with it,
this was verified against running code — the two disagreements are §3 and §4
below and both are deliberate.

---

## 1. What shipped

| | |
|---|---|
| `adopt/adopt/sdk/mcp_tools.py` | The tool module. Sixteen tools, the `TOOL_SCOPES` table, the per-call environment (`ToolEnv` / `use`), `ClientBackend` (HTTP), `register_tools`, `build_server`, `serve_stdio`. Under `sdk/`, so it imports no server code and installs on a laptop. |
| `adopt/adopt/sdk/cli.py` | `vlab mcp` — the stdio transport. Three lines, and `mcp` is imported inside them. |
| `adopt/adopt/sdk/study.py` | `push_sections`, `PushResult`, `PushRefused`, `PushFailed` — the push loop lifted out of `cli.push` so the tool cannot own a second copy of it. |
| `adopt/adopt/sdk/client.py` | `http_error()` split out of `VlabClient._error`, so the in-process backend can raise the exceptions the wire raises. |
| `adopt/adopt/server/mcp_server.py` | `POST /mcp`, and POST only (§6). The stateless streamable-HTTP transport, `InProcessBackend`, the per-tool `authorizer`, the app lifespan, the mount. The **only** file that imports both `adopt.sdk` and `adopt.server`. |
| `adopt/adopt/server/server.py` | `FastAPI(lifespan=mcp_lifespan)`, `mount_mcp(app)`, and `CONF_POST_HANDLERS` derived by walking `app.routes`. |
| `adopt/adopt/server/api_keys.py` | `DELEGATED_PATHS = {"/mcp"}` and the short-circuit in `is_authorized`. |
| `adopt/pyproject.toml` | `mcp = "1.12.4"` in the MAIN dependencies; the project pin narrowed to `>=3.10,<3.11` (§5a); `pydantic` held at `~2.9.2` (§5); `httpx` and `typing-extensions` floors raised; `addopts = "-p no:anyio"`. Version → `0.1.87`. |
| tests | `sdk/test_mcp_tools.py` (52), `sdk/test_mcp_stdio.py` (6), `server/test_mcp_server.py` (43) — 101 in all. |
| docs | `documentation/agent-api.md` §6b (both transports, client config, the scope table, Known gaps), a §8 entry, and a pointer in the intro. |

The tools, with the scope each needs:

```
create_study(org, name)                              studies:write
pull_study(org, slug)                                studies:read
validate_study(sections)                             studies:read
diff_study(org, slug, sections)                      studies:read
push_study(org, slug, sections, force=false)         studies:write
compile_strata(variables, finish_question_ref,
               existing_strata, creatives, audiences) —  pure
extract_targeting(adset, properties)                 —  pure
plan_study(org, slug)                                optimize:read
apply_instruction(org, slug, index)                  optimize:write
meta_credentials / meta_adaccounts / meta_campaigns
  / meta_adsets / meta_ads                           meta:read
list_api_keys()                                      auth:read
revoke_api_key(key_id)                               auth:write
```

---

## 2. The shape, and why it is not two implementations

§16.1's requirement was one tool module served two ways. What makes that real
rather than aspirational is that a tool has **no logic**: it shapes arguments,
calls one function the CLI already calls, and shapes the result.

That held everywhere except `push_study`, where the CLI's version was a loop
inline in a click command — validate, refuse on errors, diff, write the changed
sections in `PUSH_ORDER`, and on failure report what had already landed against
an append-only table. Copying it would have been the §5 mistake (fly's
`90cdce61`) in miniature. It is now `study.push_sections`, and `cli.push` is
printing. `study.py` still opens no socket: the client is a parameter,
duck-typed on `get_confs` and `post_conf`.

The remaining coupling is the backend. Both transports hand tools an object
with `VlabClient`'s method surface, returning exactly what `VlabClient`
returns — including where it unwraps the `{"data": …}` envelope
(`meta_credentials`) and where it keeps it for `paging` (`meta_adaccounts`).
`ClientBackend` is `__getattr__` over the real client; `InProcessBackend` calls
the route handlers.

**Why the route handlers and not the routes, or the library.** Re-entering the
app over HTTP from inside a request is a second round trip for nothing.
Calling the database and Meta code directly would be a reimplementation of
every handler's ownership check, org check and error mapping — the security
half of each route, rewritten. The handlers are plain `async def`s whose only
injected dependency is the authenticated `User`, so calling them is what the
route does minus the transport. `_wire_errors` turns their `HTTPException`s
into the `VlabClient` exceptions the wire would have produced, so a tool cannot
tell which transport it is on.

**Why the environment is a contextvar.** FastMCP hands a tool only its declared
arguments. The backend and the authorizer differ per transport and, on `/mcp`,
per request. A closure at registration time would work for stdio and not for
the remote transport, so both use `use(ToolEnv(...))` — stdio wraps the whole
server run, `/mcp` wraps each request. The session manager spawns its server
task from inside that block and a task keeps its own copy of the context, so
the environment outlives the block exactly as long as the response does.

**Why the tools are `async`.** FastMCP calls a synchronous tool on the event
loop. The in-process backend has to await handlers. `ClientBackend` therefore
puts the synchronous `VlabClient` on a worker thread, and `push_study` — which
runs the synchronous `push_sections` on a worker thread — hands its calls back
to the loop through `_CallableFromThread`. Two hops each way, and a test with
no mock in it (`test_the_http_backend_drives_a_real_app_from_the_event_loop`),
because a deadlock there would look like a hang rather than a failure.

---

## 3. Where the brief was wrong: the scopes on plan and apply

§16.2's table gives `plan_study` and `apply_instruction` **`studies:write`**.
The routes they call do not: `GET /{org}/optimize/{slug}` is `optimize:read`
and `POST …/instruction` is `optimize:write` (`api_keys.required_scope`).

Following the table would have made `POST /mcp` a way for a `studies:write` key
to run the optimizer and launch ads — the exact privilege `optimize` was cut
out of `studies` to keep separate (`api_keys.py`: "an optimize instruction
spends money on Meta"), and one that key does not have over HTTP. It would also
have made the two transports demand different scopes for the same tool, which
would have made the drift guard meaningless.

§16.3 states the rule that settles it: the table "reproduces what the routes
enforce", evaluated "with the same `scope_grants` function the routes use".
Where the two halves of the brief disagree, that rule wins. Pinned by
`test_the_scopes_are_the_ones_the_routes_require`.

**A third, smaller divergence.** §16.2 gives the key tools "`keys:*` as already
defined in the routes". There is no `keys` resource: the vocabulary is
`api_keys.RESOURCES`, and key management is `auth`. `list_api_keys` and
`revoke_api_key` are therefore `auth:read` and `auth:write`, which is what
`required_scope` returns for `/users/api-keys` and what the routes' own
`require_scope` dependencies demand. The brief's own words -- "as already
defined in the routes" -- pick the same answer; only its shorthand was wrong.

All three are covered by one test rather than three:
`test_each_tools_scope_is_what_its_route_requires` compares `TOOL_SCOPES`
against `api_keys.required_scope` for the fourteen route-backed tools. Written
that way deliberately -- an earlier version compared the table to a second
hand-written table, which asserted only that someone had typed the same thing
twice.

## 4. Where the brief was wrong: the boundary test

§16.5 says "the existing static test that `adopt/sdk/` never imports
`adopt.server` must still pass". It exists (`adopt/test_confs.py`), and it did
not pass — not because the tool module violates the boundary, but because the
test matched **any** dotted path with a `server` segment anywhere in it. `from
mcp.server.fastmcp import FastMCP` is a third-party package with an unlucky
name. Fixed to match a relative `..server` or an absolute `adopt.server`, which
is what it was always trying to say.

§16.5 also refers to an existing test that `vlab --help` stays fast. There was
none — only the *practice*, recorded in `authoring/templates.py`'s `_marketing`
docstring. There is one now
(`test_vlab_help_does_not_load_mcp_or_cvxpy`), a subprocess that runs
`--help` and asserts neither `mcp` nor `cvxpy` is in `sys.modules` afterwards.
An in-process check would pass vacuously: the test suite imports both.

---

## 5. The dependency, and what it dragged in

`mcp` is pinned to **1.12.4** exactly, in the MAIN dependencies (§16.4: the
service needs it for `/mcp`, so the `sdk` extra is the wrong place).

Two constraints picked the version. Every `mcp` release requires Python ≥ 3.10
while this package declares `>=3.9,<3.11`, so poetry needs a
`python = ">=3.10"` marker on the dependency to resolve at all — on a 3.9
install `vlab mcp` fails with "No module named mcp", which is honest. And
`mcp` 1.13 raised its floor to `uvicorn>=0.31.1` while the service runs
`uvicorn ^0.24`; 1.12.4 is the newest release whose floors this project already
meets. Bumping the ASGI server at the same time as mounting a new route would
have been two deployment risks in one change rather than one.

It was not a free addition. Four consequences, all absorbed in one commit:

1. **httpx `^0.25.2` → `>=0.27.1,<0.29`.** Every `mcp` release requires
   `httpx>=0.27`. httpx is used here by FastAPI's `TestClient` and one ASGI
   test; neither pins a 0.25 behaviour.
2. **pydantic 2.5.2 → 2.9.2** (`mcp` floors it at 2.8), and **pinned to
   `~2.9.2` rather than left on a caret**. 2.9 emits `enum` and `type` alongside
   `const` in JSON Schema, so the committed schemas were regenerated — a richer
   schema for unchanged models. The pin is the point: `make check-schemas`
   compares the committed schemas against what pydantic renders, and the
   rendering moves between minors. `Literal["app"]` is `{const, title}` on
   2.5.2, `{const, enum, title, type}` on 2.9.x, and `{const, title, type}` on
   2.13 — the `enum` appears and then disappears again. Under `^2.5.2` the next
   unrelated PR that re-resolved the lock would have failed `check-schemas` for
   no reason its author could see. Moving the pin is now a deliberate act: bump
   it, run `make schemas`, commit the result in the same change. Ideally under
   VIR-47, with the Python pin.
3. **pydantic 2.9 parses a bare `2026-06-01` as midnight**, where 2.5 refused
   it. An unquoted `start_date` in a study file is therefore now valid rather
   than a local `section.invalid`. Strictly more permissive; nothing that used
   to be accepted is rejected. The test that pinned the old verdict now pins
   the invariant it was really there for — that `validate` judges exactly the
   bytes `push` sends.
4. **anyio 3 → 4**, whose pytest plugin imports `_pytest.scope`, a module
   pytest 6 does not have. Merely installing it broke collection of the whole
   suite. Disabled with `addopts = "-p no:anyio"`; nothing here uses it (the
   async tests drive their own loop with `asyncio.run`). Bumping pytest 6 → 8
   is a change to how ~2300 tests run and has nothing to do with MCP.

Those four are the ones that changed BEHAVIOUR. The full lock delta is larger
and is recorded in `pyproject.toml` next to the `mcp` entry so nobody has to
diff a 600-line lockfile: nine packages added, one dropped (`sniffio`, which
anyio 4 no longer needs), and seven moved — anyio 3.7.1 → 4.14.2, attrs
21.4.0 → 26.1.0, httpx 0.25.2 → 0.28.1, pydantic 2.5.2 → 2.9.2, pydantic-core
2.14.5 → 2.23.4, python-dotenv 0.19.2 → 1.2.3, typing-extensions 4.9.0 → 4.16.0.
The three not listed above are transitive and were exercised only by the suite
passing.

`typing-extensions >= 4.13` is also declared, and it is not a direct import:
`mcp` uses PEP 696 TypeVar defaults and declares no floor of its own. The lock
held 4.9.0 and `import mcp` died with "Too few parameters for RequestContext",
a long way from its cause. The floor makes that a resolver error instead.

---

## 5a. The route is inert; the deploy is not

§16.6 says "the `/mcp` route is inert until a client uses it, so the values bump
carries no user-facing risk". The first half is true and the second is not, and
it is worth being precise about why.

`server/server.py` imports `server/mcp_server.py` at module scope, and
`mcp_server` imports `mcp` and builds the `FastMCP` instance at import.
`server.py` also passes `mcp_server.lifespan` to `FastAPI(...)`, so the
transport's session manager starts with the app. An `mcp` that fails to import,
or a session manager that fails to start, therefore takes the WHOLE conf service
down -- `/health` included -- rather than degrading `POST /mcp`.

That is the right trade, and it is kept: a service that boots while
half-serving a transport it advertises is worse than one that refuses to boot
and gets rolled back, and the alternative (a lazy import behind a try/except,
with `/mcp` answering 503) hides a broken deploy behind a route nobody watches.
But it means this release carries ordinary deployment risk rather than none,
and the release note in `documentation/agent-api.md` §8 and §6b's Known gaps
now say so instead of repeating "inert".

The direct consequence is the Python floor. §16.4 assumed `python =
">=3.9,<3.11"` could stay, with a `python = ">=3.10"` marker keeping `mcp` off
3.9 installs. That was true when only `vlab mcp` needed it -- "No module named
mcp" is an honest answer from a CLI subcommand -- and false once the SERVICE
imports it: on 3.9 the marker would leave `mcp` uninstalled and
`import adopt.server.server` would raise. The pin is now `>=3.10,<3.11` and the
marker is gone. Nothing was actually running on 3.9 (`Dockerfile` is
`python:3.10-slim`, CI is `python-version: '3.10'`, and the SDK install line has
said `--python python3.10` since Phase 3), so this narrows a claim rather than
dropping support. The ceiling stays at `<3.11` for pandas 1.5.3 / numpy 1.x;
VIR-47 is where both ends move.

---

## 6. Three things that bit, and are pinned

**`GET /mcp` was a denial of service, and review caught it.** The endpoint was
mounted with `Route(MCP_PATH, endpoint=MCPEndpoint())` — a class instance, so
`methods` stayed `None` and every verb matched — and handed everything to
`manager.handle_request`. Streamable HTTP defines GET (open a server-to-client
SSE stream) and DELETE (end a session) alongside POST; in STATELESS mode both
are meaningless, and the library does not say so.
`StreamableHTTPServerTransport._handle_get_request` has no session-id guard to
fail on when `mcp_session_id` is None, so it opens an `EventSourceResponse`
that can never receive anything and never closes. Each such GET pinned a
connection, a transport and an anyio task in the lifespan task group for the
life of the worker.

Reachable by ANY authenticated key, including one scoped to nothing at all:
`/mcp` is a delegated path so the middleware lets a key through before any
scope is looked at, and a GET never calls a tool, so `TOOL_SCOPES` never runs.
Reproduced before fixing — a single unfixed GET through `TestClient` had to be
killed after 90 seconds.

Fixed in two places, belt and braces the way `meta.py` pairs its `require_scope`
dependency with the scope middleware: `mount()` declares `methods=["POST"]` so
Starlette answers first, and `MCPEndpoint.__call__` refuses anything but POST
itself, so the endpoint is safe however it is mounted. The check is BEFORE
authentication, because `verify_tokens` fetches Auth0's JWKS over the network
for an RS256 token and a verb this endpoint does not serve must not cost an
outbound request. Six tests, and the ones that matter carry a `timeout`: without
the fix they do not fail, they stop.

The general lesson is worth keeping: mounting a third-party ASGI app means
inheriting every method it will answer, and "the transport only makes sense for
POST" is not something the transport enforces.



**A `StreamableHTTPSessionManager` can be `run()` exactly once per instance.**
The first version built one at module import. That works in production, where
the app's lifespan runs once, and breaks every test after the first: the second
`TestClient` context manager raises. It is now built inside the lifespan and
kept on `app.state`.

**`POST /mcp` needs that lifespan, and a bare `TestClient(app)` does not run
it.** Only `with TestClient(app) as client` does. Without a guard the endpoint
hits `assert self._task_group is not None` inside the library and answers 500,
which reads as a bug in the request rather than in how the app was assembled.
It answers 503 naming the cause instead. Pinned by
`test_the_transport_answers_503_when_the_lifespan_did_not_run`.

---

## 7. Testing, and what was not tested

The suite is 101 new tests in three files, and they split by what they need:

- **`sdk/test_mcp_tools.py`** — no database, no HTTP. One test per tool
  asserting which backend method it calls with which arguments and that the
  result comes back unchanged; the description tests (a length floor, the scope
  named, the side effects stated); the environment and guard tests; the
  `vlab --help` subprocess test.
- **`server/test_mcp_server.py`** — the §16.3 scope tests and the drift guard
  need no database and run anywhere; the runbook through `POST /mcp` with a
  scoped API key needs one.
- **`sdk/test_mcp_stdio.py`** — the runbook through the stdio server object
  against a `TestClient`-backed `VlabClient`, plus two `vlab mcp` wiring tests
  that need no database.

**The stdio test drives the server object, not a subprocess.** `serve_stdio` is
`build_server()` plus a `use()` plus the library's own loop over stdin and
stdout; a subprocess would exercise that loop and nothing else of ours, and
could not be pointed at a `TestClient`. The in-memory client covers
registration, schemas, dispatch, serialisation and the tools. What it leaves
untested is the pipe itself, which is the library's, and the command's wiring,
which has its own test.

**Not exercised, and listed in `agent-api.md` §6b's Known gaps:** neither
transport driven by a real MCP client against the deployed service; the
`initialize` handshake (stateless mode does not require it); long calls against
a real client's tool timeout; concurrency between two agents on one study;
`compile_strata` regenerating a study with ads already delivering.

CI also caught two premises this file's author had wrong, and both are worth
knowing. `GET /confs` does **not** check that the study exists, so
`pull_study` on a nonexistent slug is `{}` with all nine in `never_written`
rather than a 404 -- `vlab pull` has always behaved that way (it writes a file
with zero sections), so the tool inherits it rather than growing a check the
command does not have; the description says so. And the CLI had its own twin of
the unquoted-date test, which the pydantic bump flipped for the same reason as
`test_study.py`'s.

**Not run locally:** every database-backed test. Docker on the development
machine could not start a container at all (`failed to create shim:
unsupported protocol: Yunix`), so the CockroachDB the suite needs was
unavailable and those tests ran only in CI. Everything that does not need a
database — including the whole scope surface, the drift guard, the tool
call-through tests and the `ClientBackend` thread plumbing — was run locally
and passes.

---

## 8. Out of scope, and still open

Deliberately not done (§16.7):

- **Template creation as a tool.** It needs a Facebook token and an image
  upload, neither of which belongs behind a vlab API key, and there is no
  `meta:write` route. `vlab template` stays CLI-only
  (`agent-study-authoring.md` §10).
- **A Meta write proxy.** Same decision, not reopened.
- **Resources, prompts, sampling.** Tools only.
- **Caching.** Every `meta_*` call is a live Graph read. A cache would need an
  invalidation story that nothing here has.
- **Any tool smarter than the command it wraps.** In particular there is no
  "apply the whole plan": reconciliation is layered, so a list applied in one
  pass is a list computed before most of it was true.

Open, and worth doing next:

- **A real-client smoke run.** The single biggest gap. Point Claude Desktop at
  `vlab mcp` against a staging study and walk the runbook.
- **`vlab check --live`** (`agent-study-authoring.md` §10) would give
  `validate_study` a Meta-aware sibling that is not `plan_study`, which is the
  only Meta check today and which writes.
- **VIR-47** (pandas 2 / numpy 2, lift the Python pin). Newer `mcp` releases
  raise their Python and uvicorn floors; 1.12.4 is already a version behind for
  that reason.
