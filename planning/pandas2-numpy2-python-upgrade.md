# VIR-47: pandas 2 / numpy 2 / Python floor-lift

Plan written 2026-09-06 on `chore/adopt-pandas2-numpy2-python-upgrade`, before
implementation. Update this file with what actually shipped (in the style of
`planning/mcp.md`) once the suite is green — don't leave it as a stale plan.

## 1. Why, and what's already in place

`adopt/pyproject.toml` pinned `pandas = "1.5.3"` exactly and `python =
">=3.9,<3.11"` (later narrowed to `>=3.10,<3.11` the same day `mcp` landed,
see that block's comment). pandas 1.5 has no wheels past Python 3.11, so
nothing above it can move until pandas does. This blocks `pipx install
adopt[sdk]` on any laptop whose default Python is >=3.12 (see
`planning/vlab-sdk.md` known gaps), and it's the reason the Dockerfile is
still `python:3.10-slim`.

Two forward-pointers already in `pyproject.toml` name this ticket directly:
the Python-floor comment ("the ceiling stays at <3.11 for pandas 1.5.3 /
numpy 1.x; VIR-47 is where it gets lifted") and the `mcp` comment ("Revisit
[the uvicorn/mcp pin] together with VIR-47").

## 2. Deliberately OUT of scope for this change

The `mcp` comment invites bumping `uvicorn` (to unlock `mcp` 1.13+) "together
with VIR-47", and the `pytest.ini_options` comment invites dropping `-p
no:anyio` "when pytest is bumped". Both are declined here:

- **uvicorn/mcp**: the existing comment calls bumping the ASGI server at the
  same time as the new `/mcp` route "two deployment risks in one change
  rather than one" — that reasoning doesn't change just because a *different*
  change (pandas/numpy) is also happening. Bundling it in would make a test
  failure ambiguous between three unrelated causes instead of two.
- **pytest 6 -> 8**: explicitly called out as "a change to how ~2400 existing
  tests run and has nothing to do with MCP" — equally true of pandas/numpy.
  It's a real follow-up, just not this one.
- **pydantic** (`~2.9.2` -> newer): the comment says "ideally under VIR-47,
  with the Python pin", and it's cheap (`make schemas` + commit), but it's
  still an unrelated axis of change with its own regeneration step. Left as a
  same-week follow-up PR, not folded in, so a schema diff never has to be
  disentangled from a pandas dtype diff in the same review.
- **facebook-business** (`v22` -> `26.0.1`): no `requires_python` on either
  version (pure-Python, `requests`-based) — it isn't blocking anything on the
  new Python floor. Bumping it changes the Graph API version used for live ad
  calls, which is a product-risk decision, not a compatibility one. Left
  alone; flagged for its own ticket if VIR-47's author wants it.

This keeps the diff to exactly what the ticket's scope list says: pandas,
numpy, the deps that float on top of them (scipy, cvxpy, ecos), psycopg
(needs a floor bump for Python 3.12 wheels — see §4), and the Python
range/Docker base/CI/docs that gate all of it.

## 3. Target versions (checked against PyPI metadata 2026-09-06)

| package | from | to | why this ceiling |
|---|---|---|---|
| python | `>=3.10,<3.11` | `>=3.10,<3.13` | ecos wheels stop at `cp312` (2.0.14 is current *and* latest — no newer release to lift this). cvxpy and scipy could go further alone; ecos is the binding constraint, exactly as the ticket anticipated ("as far as cvxpy/ecos allow"). Building ecos from sdist for 3.13 would add a compiler toolchain to the Docker image for one package — not worth it for a single extra minor. |
| pandas | `1.5.3` | `^2.2` (resolves ~2.3.3) | latest 2.x; caret keeps us off pandas 3 (already on PyPI, out of scope — ticket says "pandas 2.x"). `requires_python >=3.9`, no floor conflict. |
| numpy | `^1.22.1` | `^2.2` | 2.2.6 is the newest 2.x release that still supports Python 3.10 (`requires_python >=3.10`; 2.3.x moved the floor to 3.11). Picking `^2.2` rather than open-ended `^2.0` keeps poetry from resolving something that silently drops our floor later. |
| scipy | `^1.6.3` | `^1.15` (resolves ~1.15.3) | 1.15.3 is the newest scipy that still supports Python 3.10 (1.16 raised the floor to 3.11). Satisfies cvxpy's `scipy>=1.13.0`. |
| cvxpy | `^1.5` | `^1.5` (unchanged constraint; resolves to whatever's newest under the 3.10 floor, ~1.7.x) | cvxpy versions with cp310 wheels already extend past our numpy/scipy picks; no need to move the constraint, just re-lock. |
| ecos | `^2.0` | `^2.0` (unchanged; still resolves to 2.0.14) | no newer release exists. |
| psycopg | `^3.0.9` | `^3.2` | `psycopg[binary]` has no cp311/cp312 wheels before 3.1.19, and 3.0.x tops out at cp310. `^3.2` picks a release line with cp310-cp314 wheels, comfortably covering the new ceiling with headroom. |
| facebook-business | `v22` | unchanged | see §2. |

`poetry lock` resolves the exact patch versions; the table above is the
floor/ceiling reasoning, not a hand-picked lockfile.

## 4. Phasing (small, testable steps — not one big-bang commit)

1. **Phase A — numeric stack, Python floor unchanged (3.10 only).** Bump
   pandas/numpy/scipy/psycopg per §3, leave `python = ">=3.10,<3.11"`
   untouched. `poetry lock`, `poetry install`, run the full suite
   (`make test-db && make test`), fix every pandas-2 / numpy-2 behavior
   break (chained-assignment, dtype inference, `Series.append` removal,
   `np.float_`/`np.int0`-style removed aliases, etc.) until it's green. This
   isolates "did the libraries change behavior" from "did the Python version
   change behavior" — two different failure classes that are much harder to
   tell apart if bumped together.
2. **Phase B — lift the Python ceiling.** Change `python = ">=3.10,<3.13"`,
   install a 3.12 interpreter (`pyenv install 3.12.x`), re-`poetry lock`
   under 3.12, re-run the full suite under 3.12. Bump `adopt/Dockerfile`'s
   base image to `python:3.12-slim` and `.python-version` to match. Bump the
   `adopt.yaml` CI workflow's `python-version` for both jobs; add 3.10 to a
   matrix on the `tests` job so the floor is actually exercised in CI, not
   just claimed in `pyproject.toml`.
3. **Phase C — docs.** Drop `--python python3.10` from `adopt/README.md` and
   `documentation/agent-api.md`'s pipx install lines; update the prose that
   states the `>=3.9,<3.11` / `>=3.10,<3.11` constraint.
4. **Phase D — release.** Per `planning/release-process.md`: PR review, merge
   to `main`, then `scripts/release.sh adopt <version>` (tag -> push -> verify
   GHCR image exists -> only then would a values bump follow, though this
   ticket doesn't require one). This step needs the user's go-ahead before
   anything is pushed or tagged — not run automatically by whichever agent
   does Phases A-C.

Each phase is its own commit. If Phase A's fixes turn out to be extensive,
commit it in sub-chunks by module (recruitment data, budget/optimization,
`authoring/sheets.py`, reports) rather than one monolithic diff, per
`CLAUDE.md`'s incremental-progress principle.

## 5. Definition of done

- `poetry lock` clean, `poetry check` passes.
- Full adopt suite green under Python 3.10 AND 3.12 locally (baseline test
  count re-measured on this branch before starting, since `main`'s count has
  moved past the ticket's "2642" since it was filed — most recently by the
  MCP phase's own 101 tests).
- `make check-schemas` still passes untouched (pydantic pin didn't move, so
  it should be a no-op check, not a guarantee to skip).
- Docker image builds on `python:3.12-slim` and boots (`python ./malaria.py`
  at least imports without error).
- CI green on the PR.
- README / agent-api.md no longer mention `--python python3.10`.
- Nothing pushed, tagged, or released without explicit confirmation.

## 6. Phase A: what actually shipped (2026-09-06)

Green on Python 3.10: **2754 passed, 1 skipped**, against a pre-change
baseline of 2753 passed / 1 skipped / 1 failed. `poetry check` and
`make check-schemas` both pass. `python` is still `">=3.10,<3.11"` — Phase B
has not been started.

Resolved versions: pandas 2.3.3, numpy 2.2.6, scipy 1.15.3, psycopg 3.3.5,
openpyxl 3.1.5. cvxpy/ecos/facebook-business constraints untouched as planned.

Four commits, ordered so each one is green on its own (every source fix is
valid on pandas 1.5 too, verified by running the touched modules against the
old stack before the bump landed): `refactor(budget)`, `test(clustering)`,
`test(budget)`, then `build(adopt)`.

### The one dependency §3 missed

**openpyxl** had to move from `^3.0.9` to `^3.1`, and it is not cosmetic:
pandas 2.2 raises its minimum to 3.1.0 in `pandas.compat._optional.VERSIONS`
and `read_excel` raises `ImportError` below it. The old range technically
admitted 3.1, but the lock held 3.0.9, so all of `authoring/sheets.py` died
until the floor was stated explicitly. Any future pandas bump should re-check
that table rather than trusting caret ranges.

### The only behaviour change that needed judgement

`test_proportional_budget_with_max_recuits_optimizes_for_weights` asserted
`round(expected["bar"]) == 50` where the exact optimum is `103 * goal - 1` =
50.5. It passed only via Python's round-half-to-even; scipy 1.15's L-BFGS-B
stops at 50.50058 instead of at-or-below 50.5, and `round()` flips to 51.
**No optimum moved** — the closed-form optimizer still hits 29.9 / 50.5 / 19.6
exactly, which is how we know. Now asserted with `abs=0.01`.

Worth knowing for Phase B: that test is parametrized over both optimizers, and
only the `lbfgs` arm is sensitive to solver-level float noise. If a Python or
BLAS change shifts results again, check the closed-form arm first — if it
still hits the analytic values, the objective is fine and only the iterate
moved.

### pandas 3 debt paid down while here

`GroupBy.apply` over the grouping column (deprecated 2.2, removed in 3) was
fixed rather than silenced in `budget.py` and `test_clustering.py`. In both,
the callback read the grouping column, so the suggested `include_groups=False`
remedy would have *broken* the code while quieting the warning. The suite now
emits zero pandas or numpy warnings; the 99 that remain are pre-existing
(marshmallow/distutils, pytest-asyncio vs pytest 6, facebook-business enums).

### Two local-environment traps, not code problems

- `make test-db` could not run: this host's docker daemon cannot start
  containers (`unsupported protocol: Yunix` — a containerd shim mismatch
  needing a root restart of dockerd). Worked around by `docker cp`-ing the
  cockroach binary out of the image and running `start-single-node` on
  port 5433 directly, then applying `devops/migrations/*.up.sql` in order with
  the cockroach SQL client. The DB-backed tests did really run.
- `test_no_api_key_says_a_human_has_to_mint_one` fails on any machine whose
  shell exports `VLAB_API_KEY`: click picks it up via `envvar=` and overwrites
  the `api_key: None` the test injects, so the guard under test never fires and
  a real HTTP request goes out. This is the one baseline failure, it is
  unrelated to VIR-47, and it passes under `env -u VLAB_API_KEY`. Arguably the
  test should set `VLAB_API_KEY` to empty rather than relying on the ambient
  environment — its own small ticket.
