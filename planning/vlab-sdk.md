# Phase 3: the vlab SDK and CLI

Implemented 2026-09-05 on `feature/vlab-sdk`. This is the phase-notes file for
Phase 3 of `planning/agent-study-authoring.md` §8, written in the discipline of
that document's §11–§14: what shipped, the decisions with their reasons, what
the plan got wrong, and what is deliberately not done or still open. Where this
disagrees with §8's four-line sketch of Phase 3, this was verified against
running code and §8 was a sketch.

§14 was "Phase 3a", the validation half. This is the rest of it. Phase 4 (MCP)
is unstarted and is now small, which was the whole argument for doing the SDK
first.

---

## 1. What shipped

| | |
|---|---|
| `adopt/adopt/sdk/client.py` | The HTTP client. Auth header, base URL, a typed exception for each of 401/403/404/409/422/5xx (a 400 -- which study creation and the Meta proxy both return -- lands on the base `VlabHTTPError`), `detail`'s three shapes rendered legibly, no retries. Takes an injectable `requests`-compatible session. |
| `adopt/adopt/sdk/study.py` | The file on disk: load, save, diff against the store, push ordering, unknown-key detection. Pure — no sockets. |
| `adopt/adopt/sdk/cli.py` | `click`. Sixteen commands: seven at the top level, plus the `meta`, `strata` and `keys` groups. |
| `adopt/adopt/authoring/sheets.py` | Salvaged: `parse_kv_sheet`, `parse_row_sheet`, `read_share_lookup`. |
| `adopt/adopt/authoring/geo.py` | Salvaged: `location_levels`, and `create_location` made public. |
| `pyproject.toml` | `[tool.poetry.extras] sdk = ["click"]`, `[tool.poetry.scripts] vlab`. |
| tests | `test_client.py`, `test_study.py`, `test_cli.py`, `test_sheets.py`, `test_geo.py` — 186 in all. |
| docs | `documentation/agent-api.md` §6 rewritten around the SDK (§6.1) with raw HTTP kept as §6.2; new §8 entry; §2.3 and §7.3 corrected. `adopt/README.md` gains an SDK section. |

Whole suite **2231 → 2417 passed**, 1 skipped (pre-existing), no regressions.

The commands, as built:

```
vlab create <org> <name> [--init [PATH]] [--json]
vlab pull <org>/<slug> [-o PATH] [--force]
vlab validate [PATH] [--remote] [--json]
vlab diff [PATH] [--json]
vlab push [PATH] [--section X]… [--force] [--dry-run] [--json]
vlab plan <org>/<slug> [--json]
vlab apply <org>/<slug> <index> [--yes] [--json]
vlab meta credentials|adaccounts|campaigns|adsets|ads   --org … [--json]
vlab strata generate [PATH] [--finish-question REF] [--dry-run]
vlab strata extract-targeting <adsets.json> <prop>… [--name NAME]
vlab keys list|revoke
```

---

## 2. The decision the whole diff rests on

**A diff compares what would be STORED, not what would be sent.**

`create_conf` stores `config.model_dump()`, not the request body
(`agent-api.md` §2.1). Two consequences on every single write: unknown keys are
gone, and defaults are filled in. POST a `general` conf without
`extra_metadata` and the store holds `"extra_metadata": {}`; POST a
`messenger` destination and the store gains `additional_metadata: null` and
`ref_mode: null`.

So a diff that compares the file against `GET /confs` naively reports a change
on every section whose file omits an optional field — which is most of them,
because a readable study file omits optional fields. And that is not a cosmetic
bug: `vlab push` writes what the diff says differs, `study_confs` is
append-only, and there is no delete. A permanently-wrong diff appends a row on
every push, forever, and none of them can be removed.

`normalise_section` therefore runs both sides through the same pydantic model
and `model_dump(mode="json")`s them. `mode="json"` and not `"python"`: the
stored value went through `orjson.dumps`, so `start_date` comes back as
`"2026-01-01T00:00:00"`, and a `datetime` object on our side would make every
recruitment conf differ from itself. A section that does not parse falls back to
raw comparison.

The **lenient** models, not PR #262's strict twins, following the reasoning
already written into `authoring/validate.py`: what a diff asks is "does the
store hold what my file says", and the store is read by `StudyConf` on the run
path.

`test_a_section_round_trips_through_the_real_storage_path` and
`test_a_datetime_survives_the_round_trip_as_a_comparable_string` exercise this
against the real app rather than against an assumption about `model_dump()`.

---

## 3. Version skew, and the `type` tag

PR #262 (`feature/conf-strict-writes`, in flight) tags the recruitment union
with `simple` / `pipeline_experiment` / `destination`, so `model_dump()` starts
writing a `type` into storage. A server older than it drops the tag on the way
in, because `extra="ignore"` eats it.

The SDK writes the tag — new configuration should be explicit about which arm
of a union it is, and §11.4 item 3 is the reason the union is being tagged at
all. But then:

| The file | The server | Naive diff says |
|---|---|---|
| writes `type` | #262 or later: stores it | unchanged ✓ |
| writes `type` | older: drops it | **changed, forever** ✗ |
| omits `type` | #262 or later: stores the inferred one | **changed, forever** ✗ |

Both failing rows append a row to an append-only table on every push. So
`_strip_inferred_tag` removes a `type` whose value equals what the body's own
shape would have been tagged with — from either side, symmetrically. The same
rule covers a `messenger` destination, whose absent `type` the server defaults
in (`_default_missing_destination_type`) for the 45 stored confs that predate
the field.

**The inference is not reimplemented if it can be imported.**
`infer_recruitment_type` prefers `study_conf._infer_recruitment_type` and falls
back to a copy. Once #262 lands there is one definition; until then the copy
reproduces its test order — `ad_campaign_name` → `arms` → `destinations` —
which is load-bearing, because a body carrying both `arms` and `destinations`
resolves to the pipeline arm under today's untagged union and a diff that
decided otherwise would claim a study's recruitment strategy had changed.

**A tag that contradicts the shape is not tolerated, but where it surfaces is
version-dependent, and that is correct.** On a server older than #262,
`type: "destination"` on a body with `ad_campaign_name` is an undeclared field:
the server drops it exactly as normalisation does, so pushing really would
store what is already stored, and calling that "changed" would be false. It is
reported instead as an unknown key — `_is_exempt_tag` exempts only a tag that
restates the shape. From #262 onwards the same body is a 422 from the
discriminated union, and `push` reports that.

---

## 4. Unknown keys: reported, but not by `validate`

Every conf model runs on pydantic's default `extra="ignore"` (§11.4 item 2), so
a misspelled *optional* field is accepted with a `201` and silently discarded.
§11.5 and §14.6 both say this is the open defect that most undercuts the
validator, and §14.6's phrasing is the right one: "a validator that reports a
study clean while the server silently dropped a misspelled optional field is
telling a true answer to the wrong question."

The SDK reports them, and the detection needs no model introspection: parse the
section, `model_dump()` it, and anything present in the input and absent from
the dump was dropped — at any depth, through unions, through lists. Pydantic is
the oracle. Arbitrary-key fields (`facebook_targeting`, `template`, `metadata`,
`extra_metadata`, `data_sources[].config`) produce no false positives, because
they are `Dict[str, Any]` and the dump keeps everything.

**They are reported by `diff` and `push`, and deliberately not by `validate`.**
`vlab validate` is a wrapper over `authoring.validate.validate_study` and has to
give the same answer as `POST /{org}/studies/{slug}/validate`, which uses the
same lenient models and does not report them. Adding a finding that only the
local half produces would break exactly the property that makes `--remote`
meaningful. An undeclared key is a fact about the *wire*, not about the study,
so it belongs in the commands about the wire.

This is not a fix for §11.4 item 2, and does not claim to be: it is a client
telling you what the server is about to do. #262 is the fix.

---

## 5. Decisions worth their own line

**Push order is fixed, and it is not for the server.** general → destinations →
creatives → audiences → variables → strata → data_sources → inference_data →
recruitment. The server checks nothing across sections, so the order buys the
server nothing. It buys two things: a push that stops half way — a 422 on
creatives, a dropped connection — leaves a *prefix* of the reference graph on
the server rather than a middle of it, so no stratum is ever stored naming a
creative that was not written; and `recruitment` last means the `adopt-ads`
cron, which only touches studies where `start_date < now < end_date`, cannot
pick the study up half-configured. Runbook step 9 already said the second.

**No retries, anywhere.** Not on writes: `study_confs` is append-only, a POST
that timed out may well have inserted a row, and there is no idempotency key
and no way to withdraw the duplicate. Not on reads either — a weaker argument,
made so that "the SDK does not retry" is one sentence a user can hold rather
than a rule with an exception. `GET /{org}/optimize/{slug}` is what makes the
simplicity worth it: it looks like a read, it is documented as a preview, and
it writes three report rows and heals ad attributions every time (§11.3). A
retry policy keyed on the HTTP method would have retried it. The Meta proxy's
`502` is the one place the API says "retry"; the exception carries the status so
a caller can, with its own backoff.

**`vlab apply` re-plans rather than caching.** The index is an index into a
freshly computed list. Reconciliation is layered — an ad set's ads are not
planned until the ad set exists on Meta — so a cached list is stale the moment
anything is applied, and posting a stale instruction means posting an
`adset_id` that no longer means what it did. The cost is that the plan's writes
and Meta reads happen again on every apply, which is real and is stated in the
help text.

**No token storage. No `vlab login`.** `VLAB_API_KEY` and `VLAB_API_URL` from
the environment, overridable by flags, and nothing written to disk. The one
thing an agent's working directory should not contain is a credential that can
spend money on Meta.

**No `vlab keys create`.** Minting needs a token you already have; for the first
key that is an Auth0 token, which means a browser login. A key can mint further
keys only with `auth:write` and only narrower ones. A create command would
mostly produce a confusing 403, so the group's help says who can mint instead.

**`validate` exits 1 on errors and never on warnings.** That is what makes it
usable in a `&&` chain and in CI, and the warning half stays non-fatal for the
reasons §14.2 gives: a study recruiting uniformly is entitled to a thin ref, and
one not yet wired to a survey platform is unfinished rather than broken.
`missing_targeting_variables`' false-positive rate against the production corpus
is still unmeasured, and this is the thing that would have exited non-zero on it.

**`known_gaps` is printed on every `validate`, valid or not.** What the verdict
did not cover is exactly what a caller reading "valid" is at risk of
over-reading.

**Errors are typed per status and `detail`'s three shapes all render.** A plain
string on most routes; a LIST of `{loc, msg, type}` on a 422; an OBJECT on the
Meta proxy (`{message, meta_error: {code, subcode, …}}`). Flattening the 422
list into `str(detail)` would throw away the `loc`, which is the most actionable
failure the API has. `TransportError` is separate from `ServerError` because a
`502` means vlab answered and said Meta is unhappy, while a connection failure
means nothing answered — different things to check.

**The session is injectable, and that is a test decision.** `VlabClient` takes
anything with a `requests`-compatible `request()`, so the test suite injects
Starlette's `TestClient` and drives the real FastAPI app in process. A route
that changes its path, its status or its response shape breaks these tests,
where mocking `requests` would have let it through. The only mocks are the
boundaries the app's own tests mock: `run_study_opt` /
`run_single_instruction`, and `FacebookAdsApi.call`.

**The file has no schema of its own.** Section values are the wire shapes
verbatim. The moment the file has a schema, the SDK owns a second definition of
what a study is — which is the failure that made the dashboard's TypeScript
compiler a problem (§4 of the plan). It also means `agent-api.md` §3 documents
the file format and stays correct for free.

---

## 6. The salvage of `configuration.py`

§10 asked for "a read-through against real notebook usage in `campaigns/` to
separate the still-useful composition helpers from the parts that only made
sense pre-dashboard", and §12.4 deferred it to this phase because there was no
`campaigns/` directory in this repo. There is one on the author's machine:
~170 notebooks, 46 importing `adopt.configuration`, 17 of which call anything —
the other 29 carry the import cell as copy-pasted boilerplate.

**Salvaged**, with call counts from that corpus:

| New home | Function | Usage |
|---|---|---|
| `authoring/sheets.py` | `parse_kv_sheet` | 68 call sites, 17 notebooks. Always into a pydantic model from `study_conf`. |
| | `parse_row_sheet` | 17 calls, one shape: a `creative` tab into `list[CreativeConf]`. |
| | `read_share_lookup` | 17 calls. `tab_name` is always the literal `"targeting_distribution"`. |
| `authoring/geo.py` | `location_levels` | 24 calls, 20 notebooks. |
| | `create_location` | 15 call sites across 14 notebooks — **every one a local copy**, because it was never exported. Now public. |

**Two changes, both taken from what notebook authors kept rewriting by hand.**

`location_levels` emits `facebook_targeting`, not `params`. The old key was
readable only by the old `configuration.format_group_product`; the compiler
that replaced it — `authoring.strata.create_strata_from_variables` — reads
`facebook_targeting` and `quota`, which is the dashboard's level shape and the
wire shape of a `variables` conf. Salvaging the old shape would have salvaged a
helper that composes with nothing, so there is a test that compiles a geo
variable straight through the compiler and asserts the radius targeting lands
on the stratum.

And `rows` takes anything row-shaped — a DataFrame, bare Series, dicts, or the
`list(df.iterrows())` twenty notebooks pass. The original destructured
`for _, r in rows`, welding it to that one call; three later notebooks ship
their own copy differing only in taking bare records. That coupling is the thing
people rewrote, so it is the thing that changed.

**Dropped, with the reason recorded in `configuration.py`'s marker:**

- `format_group_product` — 58 calls, the highest raw count in the corpus, and
  superseded. Its four disagreements with the dashboard (metadata keys,
  `md:` refs, hyphen-joined ids, Excel quotas) were already documented in the
  Phase 1 marker. The `variables` → `product` → `levels` *shape* is worth
  keeping; this implementation is not.
- `get_adsets`, `_get_adsets`, `get_relevant_part`, `fb_property_lookup`,
  `get_geo_name`, `make_variable_extraction`, `extraction_confs` — 36 calls,
  but a single frozen shape: `a, g, l = get_adsets(template_state,
  extraction_confs)`, always with the module constant, hard-wired to it having
  exactly three entries in one order. This is the "scrape targeting out of a
  hand-built template campaign" workflow, and the Meta proxy plus
  `extract_from_adset` is its replacement.
- `create_campaign` — 0 calls of the library version, and it is a `NameError`
  as written: it references `Instruction`, which the module never imports. 63
  notebooks define their own two-argument version (`marketing.create_campaign`
  is the live one and matches that signature).
- `respondent_audience_name` — 36 calls, and still dropped. It is one f-string,
  it encodes a notebook-era convention (`<study>-respondents`) that no code
  under `adopt/` reads, and the dashboard imposes no such convention. Putting
  it in a library would enshrine it.
- `TargetingConf` — 45 notebooks import it; it bundles a superseded field
  (`template_campaign_name`, replaced by the Meta proxy) with a plain
  `list[str]`.
- `hyphen_case`, `conf_for_export`, `_creative_conf`, `stringify_column`,
  `origin_of`, `read_single_value_share_lookup` — zero notebook callers for the
  library versions. the single-value reader moves as a private helper of the
  function that uses it; `origin_of` did not move at all -- `_cast_strings`
  inlines `getattr(hint, "__origin__", None)`, which is all it ever needed.

`configuration.py` is **not deleted**: 46 notebooks import it, and none of them
is in this repo. Its docstring now points at the new homes.

**One inherited defect fixed on the way.** `cast_strings` called `int(value)`
bare, so a typo'd number was `ValueError: invalid literal for int() with base
10: 'not-a-number'` — naming neither the field nor the sheet. An unknown column
was a bare `KeyError`, which is the likeliest failure when opening an old
workbook, since `GeneralConf` has dropped `objective` and `page_id` since these
were written. Both are now a `SheetError` naming the cell and, for the second,
listing the fields the model does accept. Naming the cell is the entire reason a
reader beats `read_excel` plus a dict comprehension.

---

## 6b. What a pre-merge review found

A read-through of the branch against the API contract (2026-09-05, before
merge), with the diff machinery exercised by simulating the real storage path
-- `TypeAdapter.validate_python` -> `model_dump()` -> `orjson.dumps` ->
`json.loads`, which is what `server.create_conf` plus `db.create_study_conf`
actually do -- over every conf shape: all three recruitment arms, all five
destination types with and without `type`, tz-aware and naive datetimes,
nested `question_targeting`, empty lists, null `tags`.

**It found no bug in §2 or §3**, which is the part that matters: every case
round-trips as `unchanged`, so `push` neither writes when it should not nor
skips when it should. What it found instead, all fixed on the branch:

1. **`vlab create --init` wrote a broken file for ordinary study names.** The
   skeleton is interpolated text, not a dumped dict, so nothing quoted the one
   piece of arbitrary user input in it. `"HPV: Lagos 2026"` and `"- dash"` made
   the file unparseable; `"#1 study"` left `general.name` null; `"Yes"` and
   `"NO"` became booleans. It is the FIRST command in the runbook and the study
   already exists server-side by then, so re-running is a 409 and the file is
   not recoverable. Everything interpolated now goes through `json.dumps`,
   which is always a valid one-line YAML scalar.
2. **A typo'd section name did nothing at all** -- not written, not rejected,
   not missed. The SDK filtered extras out of `sections` before calling
   `validate_study`, throwing away `section.unrecognized`, the only thing in
   the system that catches it. Two comments claimed it was already reported,
   via a `StudyFile.extra_keys` that did not exist. `all_sections()` now
   carries them, and `diff` names them.
3. **A malformed `study.yaml` printed a traceback**: `yaml.YAMLError` is
   neither `ValueError` nor `OSError`, so it walked past `VlabGroup.invoke`.
4. **`push --section X` claimed the whole study was in sync** when only the
   filtered sections were.
5. **`_error` treated any JSON array as FastAPI's per-field errors**, so
   `field_errors` could hand a caller dicts with no `loc` or `msg` under a name
   that promises both.
6. Three smaller: `meta ads --ad` silently ignored `--limit`/`--after`;
   `parse_target` turned `org/slug/extra` into a 404 rather than a usage error;
   `keys list` would `TypeError` on a null name.

**And one recorded rather than fixed:** the file is YAML 1.1, where a bare `NO`
is the boolean false rather than Norway. `countries: [NO]` parses, dumps as
`false`, pushes, and reads back as unchanged -- a one-time silent corruption
with no further signal. A *pulled* file is safe, because `yaml.safe_dump`
quotes it; only hand-authored files are exposed. The skeleton now warns, and
quotes its own `- "NG"`. Making the loader itself YAML 1.2 would mean a new
dependency (`ruamel.yaml`) and would change what an existing file means.

The transferable lesson is the first one: **a template that interpolates rather
than serialises has to do the serialiser's escaping job, and the test that
would have caught it is a name with a colon in it.** Every fixture in the suite
used names that need no quoting.

---

## 7. What the plan got wrong

**§8's Phase 3 is four bullets and they are all right, which is itself the
finding.** After §11, §13 and §14 each opened with a correction, this one does
not have a big one: `validate`, `push`/`diff`, `plan`, `apply`, an extra on
`adopt`, a `vlab` CLI. The reason is §14 — building the library first and the
endpoint as a wrapper meant Phase 3 was assembly rather than design, which is
exactly what §14.1 predicted when it said "the SDK does not need the *endpoint*,
but it very much needs the library".

Three smaller things:

- **§8 says "the models" are part of what gets packaged.** They are not
  packaged separately and do not need to be: the file format IS the wire shape,
  so the SDK exposes no model layer of its own, and `adopt.study_conf` is
  already importable by anyone who installs `adopt`. A `StudyConf`-typed API on
  top would have been a second definition of a study.
- **§7's packaging note — "accepts that pipx pulls pandas/scipy/cvxpy" —
  understates how little the extra adds and overstates the problem being
  weighed.** The extra is one package (`click`), because `requests`, `PyYAML`
  and pandas are already hard dependencies. The weight was never the extra; it
  is `adopt` itself, and nothing here changes that.
- **§14.6 lists "Phase 3 proper — the SDK, `vlab
  validate`/`push`/`diff`/`plan`/`apply` — is unstarted" as an open item.**
  Closed. What is still unstarted is `vlab check --live` (§8 below) and MCP.

**A claim in `agent-api.md` was disproved.** §2.3 said `GET /confs` "Raises
(→ `500`) if the study has no confs at all", and §6 step 4 said "On a fresh
study this raises; treat that as empty". Neither is true:
`db.get_all_study_confs` builds a dict comprehension over the result set, which
for no rows is `{}`, and the `except IndexError` beside it cannot fire. A fresh
study is `200 {"data": {}}`. `vlab pull` on a new study depends on this, so
there is a test pinning it. Both places in the document are corrected.

---

## 8. Deliberately not done

- **`vlab check --live`.** §14.5 named it and §10's third bullet was closed in
  its favour: the Meta-dependent half of validation — does the template campaign
  still exist, does the template ad set still carry the declared properties, is
  this `objective`/`optimization_goal` pairing one Meta accepts — is not
  checked by anything except running the plan. `vlab plan` is what an author
  has, and it is slow, it reads Meta and it writes rows. This is the most
  obviously missing command.
- **No MCP shim.** Phase 4. The SDK is now shaped for it: the smart operations
  (`validate_study`, `create_strata_from_variables`, `diff_sections`) are
  library functions with no CLI in the way, which is the refactor fly had to do
  after the fact (`90cdce61`).
- **No `vlab copy-from`.** `POST /copy-from` exists and is the dashboard's
  "Initialize", but the SDK's equivalent — pull someone else's study, change
  the header, push — is one command longer and shows you what you are copying.
  Worth adding if the extra round trip turns out to matter.
- **No `vlab watch` or polling loop.** §6.2 step 12 lists four things worth
  polling; wrapping them in a loop is a scheduling decision the caller should
  make.
- **The dashboard is not repointed at anything.** Same reasoning as §13.5 and
  §14.5.
- **`read_share_lookup`'s pandas was not rewritten.** Its original author's
  comment calls it "crazy pandas magic. Probably worth redoing from scratch",
  and four of its seventeen notebook callers shadowed it with their own version
  before calling it — so the corpus agrees. It moved unchanged anyway, because
  the five tests that pin its output are the only specification it has and a
  rewrite would be a behaviour change dressed as a move. Marked in the module
  docstring as working-for-the-shapes-it-is-tested-on rather than general.

---

## 9. Known gaps

- **The SDK has never been run against the production service.** Every test
  drives the real FastAPI app in process through `TestClient`. That covers the
  routes, the models, the SQL and the storage round trip; it does not cover the
  ingress, TLS, or any behaviour of the deployed replica that differs from a
  test client. The same gap §13.6 records for the Meta proxy, for the same
  reason.
- **`infer_recruitment_type` is two implementations until PR #262 lands.** It
  prefers `study_conf._infer_recruitment_type` when importable, so the
  duplication removes itself on merge — but nothing *enforces* that the
  fallback and the real one agree while both exist. A test asserts the fallback
  produces the documented tag for each of the three arms; it cannot compare
  against a function that is not on this branch.
- **`value_diff` matches list elements positionally.** An element inserted at
  the front of `strata` reads as "everything after it changed". That is the
  wrong answer for an insert and the right one for the common edit, and
  matching by `id`/`name` would need a per-section rule and would still be a
  guess for `question_targeting.vars`. The output is capped rather than
  bounded, so the failure mode is noise, not a wrong push — `push` writes whole
  sections and does not read `value_diff` at all.
- **`push` is not atomic and cannot be.** Nine POSTs, no transaction, no
  rollback. A failure part way leaves a prefix written (§5). Re-running is safe
  — the diff then shows only what is still outstanding — but there is no way to
  undo the prefix, because `study_confs` has no delete.
- **Two writers still lose each other's edits.** `diff` reads, `push` writes,
  and nothing detects that the store changed in between. There is no
  concurrency control on `study_confs` at all (§1.1) and the SDK adds none;
  `diff` immediately before `push` narrows the window and does not close it.
- **`vlab strata generate` merges by stratum id, and a changed id is a
  delete.** The command warns when the fresh strata no longer produce an
  existing id, because a stratum id is a Meta ad set name and pushing that
  deletes the ad set with its learning and its history. But it cannot tell a
  rename from a removal, and neither can reconciliation.
- **Whether `read_share_lookup` is correct for tab shapes outside its five
  tests is unknown**, and four notebooks suggest it is not. See §8.
- **`--remote` validation is only as fresh as the deployment.** It exists for
  the case where this package is older than the server; the reverse case — a
  newer SDK against an older server — is not detectable at all, because no
  endpoint reports the deployed adopt version. Read
  `devops/values/toixo-prod.yaml`.
- **The study file is loaded as YAML 1.1**, where a bare `NO` is the boolean
  false rather than Norway, and `y`/`on`/`off` are likewise booleans.
  `facebook_targeting` is `Dict[str, Any]`, so `countries: [NO]` parses, dumps
  as `false`, pushes, and then reads back as unchanged -- a one-time silent
  corruption with no further signal. A file written by `vlab pull` is safe
  (`yaml.safe_dump` quotes it); only a hand-authored one is exposed. The
  skeleton warns and quotes its own country code. Fixing it properly means a
  YAML 1.2 loader (`ruamel.yaml`), which is a new dependency and would change
  what an existing file means.
- **The `sdk` extra was not installed from a built wheel and tested end to
  end.** `poetry check --lock` passes, the console-script entry point resolves,
  and the CLI runs from the source tree; `pipx install 'adopt[sdk]'` from a
  built artifact was not exercised, because `adopt` is not published to any
  index and installing it means a git or path install.
