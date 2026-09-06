# Phase 4: the MCP shim

Implemented 2026-09-06 on `feature/mcp`. This is the phase-notes file for
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
| `adopt/adopt/server/mcp_server.py` | `POST /mcp`. The stateless streamable-HTTP transport, `InProcessBackend`, the per-tool `authorizer`, the app lifespan, the mount. The **only** file that imports both `adopt.sdk` and `adopt.server`. |
| `adopt/adopt/server/server.py` | `FastAPI(lifespan=mcp_lifespan)`, `mount_mcp(app)`, and `CONF_POST_HANDLERS` derived by walking `app.routes`. |
| `adopt/adopt/server/api_keys.py` | `DELEGATED_PATHS = {"/mcp"}` and the short-circuit in `is_authorized`. |
| `adopt/pyproject.toml` | `mcp = {version = "1.12.4", python = ">=3.10"}` in the MAIN dependencies; `httpx` and `typing-extensions` floors raised; `addopts = "-p no:anyio"`. Version → `0.1.87`. |
| tests | `sdk/test_mcp_tools.py` (54), `sdk/test_mcp_stdio.py` (6), `server/test_mcp_server.py` (19). |
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
meets. Bumping the ASGI server in the change that mounts an inert route would
have put deployment risk on a feature that carries none.

It was not a free addition. Four consequences, all absorbed in one commit:

1. **httpx `^0.25.2` → `>=0.27.1,<0.29`.** Every `mcp` release requires
   `httpx>=0.27`. httpx is used here by FastAPI's `TestClient` and one ASGI
   test; neither pins a 0.25 behaviour.
2. **pydantic 2.5.2 → 2.9.2** on Python 3.10 (`mcp` floors it at 2.8). 2.9
   emits `enum` and `type` alongside `const` in JSON Schema, so the committed
   schemas were regenerated — a richer schema for unchanged models.
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

`typing-extensions >= 4.13` is also declared, and it is not a direct import:
`mcp` uses PEP 696 TypeVar defaults and declares no floor of its own. The lock
held 4.9.0 and `import mcp` died with "Too few parameters for RequestContext",
a long way from its cause. The floor makes that a resolver error instead.

---

## 6. Two things that bit, and are pinned

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

The suite is 79 new tests in three files, and they split by what they need:

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
