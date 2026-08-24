# Plan: how an ad carries attribution, and how it is read back

Branch from `main`. This is a specification of the finished system: build what
it describes, and let anything already in the tree that contradicts it go.

Write code and comments that describe what the system does. State a constraint
as a property of the system — "swoosh compares the extracted value to
`ref_token` verbatim, so X" — and let the reason be the mechanism itself.

---

## 1. The shape

A recruitment ad carries a **ref**: the string that comes back when someone
clicks it. There are two questions about it, and they are independent.

| | Question | Field | Configured in |
|---|---|---|---|
| **Write** | Does the ref carry the stratum inline, or an opaque token? | `ref_mode`, on a destination | Destinations |
| **Read** | Is the value read the answer, or a token identifying the ad? | `mapping`, on an extraction conf | Data Extraction |

Independent means: neither side validates, gates or reads the other. The write
side knows nothing about channels, sources, or the rest of the study. The read
side knows nothing about which platform can carry a token. The two confs are
POSTed to separate endpoints and each saves on its own terms, in any order, at
any stage of configuration.

The one place they meet is a warning:
`thins_its_ref_without_reading_the_mapping` names destinations whose resolved
mode is not `"metadata"` while no extraction conf declares
`mapping: "ad_table_lookup"`. It warns on every reconciliation run, because a
study recruiting uniformly is entitled to a thin ref.

---

## 2. adopt: the write side

### The mode

```python
RefMode = Literal["metadata", "encoded"]
```

A ref either carries the stratum or carries a token that resolves to it. A study
with no stratification simply has a short ref, because `creative_metadata` has
nothing to put in it.

`RefModeDestination` carries exactly one field:

```python
ref_mode: Optional[RefMode] = None

@property
def resolved_ref_mode(self) -> str:
    return self.ref_mode or "metadata"
```

Optional is what keeps the migration free: a conf that states no mode resolves
to exactly the behaviour it has today, and no stored JSON is rewritten. One
field means there is nothing for a second field to contradict.

**Every destination type is a `RefModeDestination`** — messenger, whatsapp,
multi, web and app. What a ref carries is a property of the ref, not of the
channel carrying it. So `ad_ref_token` and
`thins_its_ref_without_reading_the_mapping` ask `resolved_ref_mode` of any
destination, with no type check.

The models tolerate unknown keys. Confs are stored as raw JSON and read back
through the model, so forbidding extras would stop every conf written before any
future field removal from loading, and halt that study's reconciliation.

### Serialising the ref

`dotted_ref(creative_name, metadata, destination, token)` produces the dot-pair
grammar: Messenger's `url_tags` and quick-reply payload, multi's Messenger arm,
and the `{ref}` a web or app destination interpolates into its
`url_template` / `deeplink_template`. `whatsapp_ref` is its counterpart for the
WhatsApp autofill, which fly parses under a different, `form.`-anchored grammar.

```python
if destination.resolved_ref_mode == "encoded":
    tok = _require_token(token, destination)
    shortcode = destination_shortcode(destination)
    return encoded_ref(shortcode, tok) if shortcode else tok

return make_ref(creative_name, metadata)
```

A destination with a shortcode routes through fly, whose decoder recovers the
shortcode and the token from one string, so its encoded ref is
`r.<payload>` — and `encode_recruitment_ref` requires a shortcode of 1..255
bytes. A web or app destination has no shortcode: its template already points at
the survey, nothing decodes its ref, and swoosh compares the extracted value
against `ad_attributions.ref_token` verbatim. So its encoded ref is the bare
token.

`dotted_ref` is the only place the mode is allowed to matter. `creative_metadata`
returns the complete dict under either mode, because that same dict is what
`ref_metadata` freezes into `ad_attributions.metadata` — and for an encoded
study that frozen row is the only attribution it will ever have. Pin this with
tests asserting identical frozen blobs, and identical `ad_provenance` output,
under both modes.

`ad_ref_token` mints at the grain of (study, stratum, creative, destination),
which is the grain of an ad and therefore of a mapping row.
`assert_ref_tokens_unique` refuses to publish a campaign whose ads share a
token: a collision is a wrong answer rather than a missing one, and nothing
downstream can detect it.

`check_whatsapp_refs_are_deliverable` validates, at config time, that a WhatsApp
or multi destination resolving to `"metadata"` has stratum values fly's entry
pattern can parse. It fails closed: the study creates no ads at all, rather than
ads that recruit into the fallback survey.

### The extraction conf

`ExtractionConf` validates one thing: that `mapping` is a known value.

```python
@property
def is_ad_table_lookup(self) -> bool:
    return self.mapping == MAPPING_AD_TABLE_LOOKUP
```

### The export

`csv_export.py` renders the ad→stratum mapping two ways, from one definition:

```python
headers(md_keys)          # the column list
cells(row, md_keys)       # one row's values, in that order
ad_attributions_csv(rows)   # writes them positionally
ad_attributions_table(rows) # zips them into dicts, for the dashboard
```

The columns are a union across rows in first-seen order, so the file and the
table must derive them from the same place or they will show different shapes
seconds apart. Every row is emitted, including ads Facebook no longer has:
respondents keep arriving from deleted ads through reshared page posts, and a
missing row looks like an unattributed respondent.

Serve both from the server: the CSV at
`/{org}/studies/{slug}/ad-attributions.csv`, and JSON for the dashboard table.

---

## 3. swoosh: the read side

Location says where to read; mapping says what the value means. Compose them:

```go
locationReader(location) (RetrieveFunc, error)
resolveThroughAdTable(read RetrieveFunc, attributions AdAttributions) RetrieveFunc
getRetrieveFunc(conf, attributions)  // locationReader, wrapped if it is a lookup
```

```go
func isAdTableLookup(conf *ExtractionConf) bool {
    return conf.Mapping == MappingAdTableLookup
}
```

`resolveThroughAdTable` wraps **any** reader: read a raw value, unquote it as a
token, find the row, return `row.Metadata[conf.Name]`. `Key` addresses the
token; `Name` addresses the stratum variable on the row and is also the output
name.

A lookup therefore works on either location, and that is what the whole design
buys. A respondent recruited by a fly destination brings the token back in
event metadata; one recruited by a web or app destination lands on the
researcher's own page and brings it back as a field in Typeform or Qualtrics.
Each conf declares where its own token is, and two lookup confs under one source
need not agree.

`refToken` unquotes: extracted values are JSON, so a token arrives as
`"a1b2c3d4e5"` while `ref_token` comes out of a text column bare. Joining the
raw bytes misses every single time, on a value that looks correct in every log
line it appears in. A value that is not a JSON string is not a token.

Keep the mapping as plain data closed over by the `RetrieveFunc`. It has no
context and no error and runs once per event per conf, so a database call inside
it would be one query per response. `GetAdAttributions` loads once per study in
`swooshStudy`, before `Reduce`, which keeps `Reduce` pure and testable against a
fake mapping. A row whose `ref_token` is NULL is loaded but not indexed — it has
no join key, and must not land under `""` where every tokenless respondent would
match it.

`adAttributionOutcome` reports exactly one thing, at severity `error`: a token
that resolves to no row. vlab minted an ad and lost what it meant, so every
respondent that ad recruits is dropped from stratum counts. Walk the source's
confs, skip non-lookups, ask each through its own `locationReader`, and return
on the first token that does not resolve — one event yields at most one outcome
however many lookup confs a study declares. An event carrying no token produces
nothing: that is an expected arrival, not a failure. Put `token_location`
alongside `token_key` in the details.

A token that resolves to nothing is `unmapped`. It is never retried as a raw
value and never retried against `ad_id`, which is carried on the event and
reported in the details purely so a miss can be cross-referenced against
recruitment-health signals. The outcome is self-healing: swoosh recomputes
everything each run, so inserting the missing row fixes prior runs.

---

## 4. dashboard

### 4a. The ref-mode control

`forms/destinations/refMode.ts` is the pure module; `RefModeField.tsx` is the
control, rendered by all five destination forms — Messenger, WhatsApp, Multi,
Web and App. One control rather than a copy each, so that a multi-channel study
attributes exactly one way.

`refModeOptions()` takes no arguments and returns both modes. There is nothing
to decide it from.

Label by consequence. The words `ref_mode` and `encoded` never reach the screen.
What a researcher needs is where their stratum data ends up and what the key is:
inline, so the export already has `gender` and `region` as columns and there is
nothing to join; or looked up afterwards from the ad-attributions export.

Add `ref_mode?: RefMode` to the `Web` and `App` types in `types/conf.ts`.

**The rule that carries the migration.** The encoded default is a *new-conf*
affordance and is never written onto a conf that arrived without one. An absent
`ref_mode` is a real state: the conf predates the field. Three properties hold
it, and all three are required:

1. `displayedRefMode(stored) = stored || "metadata"` reports what a conf
   actually does, and is never written back.
2. The default lives only in the two empty-state constructors —
   `Destination.tsx` `emptyStates` and `Destinations.tsx` `initialState` — both
   of which build new confs. Every type gets it, web and app included.
3. The forms spread `...data`, so a field absent from a conf stays absent
   through an unrelated edit.

Write a component test for the scenario these exist for: open a destination with
no `ref_mode`, edit its welcome message, save, and assert the saved conf still
has no `ref_mode`. Keep it passing.

Warn when a saved destination's mode is about to change. Changing it rewrites
every ad in the study on the next reconciliation run, because the ref is part of
the creative and reconciliation compares creatives: real spend, possibly another
Meta review, and the learning phase starting over. Live posts people have shared
start pointing at the new link. Existing respondents keep their attribution.
Compare through `displayedRefMode`, so that absent and an explicit `"metadata"`
count as the same thing.

### 4b. The extraction form

`extraction.ts` (pure) and `Extraction.tsx` (the component), serving fly,
Qualtrics and Typeform alike. Every source offers both locations and both
mappings; changing the location leaves the mapping alone.

`metadata` is a keyed read under either mapping — you name a key and get a
value — so there is no response path to select. `variable` is the only location
with one. Express that once, as a concept, rather than as scattered checks.

Both text fields change meaning under a lookup, and the prompts say so:

| Field | Raw read | Ad lookup |
|---|---|---|
| `key` | the key or field holding the value | the key or field holding the **token** (`vt` on fly) |
| `name` | what to call the variable | the **stratum variable** to pull, which is also what it is called |

### 4c. Read-side defaults

`generateLookupConfs.ts`. A fly source with nothing saved starts with one
`ad_table_lookup` conf per variable declared in Variables, in place of a single
blank row. The researcher already named those variables and the name is exactly
what the ad's frozen row is keyed by, so asking for them again in a different
vocabulary is what produces silent half-configs.

A default, not a merge: a source with saved confs shows those, a source without
shows these, nothing merges, and no second copy is held anywhere. Consume it in
`InferenceData.tsx`, where `initialState` is already built per source.

Fly only, because the default has to guess where the token is and `vt` is fly's
convention; another source returns it as a field only the researcher can name.

### 4d. The Ad Attributions step

A wizard step rendering the mapping as a table, with a CSV download, from
`ad_attributions_table`. Register it in `shared.ts` — whose `confs` array
doubles as the wizard's next-step chain via `getNextConf`, so adding a step
changes where the previous one advances to.

---

## 5. To remove

The tree carries these. They are not part of the system above, and the code
described in §2–§4 replaces them.

Nothing here needs a migration or a backfill. `include_metadata_in_ref` and the
`"shortcode"` mode reach no stored conf, and the models tolerate unknown keys,
so removing a field cannot stop an existing conf loading.

**adopt/adopt/study_conf.py**

- `"shortcode"` from the `RefMode` literal.
- `include_metadata_in_ref`, from `RefModeDestination` and every subclass.
- the validator `ref_mode_must_not_contradict_the_legacy_flag`.
- the validator `a_lookup_reads_the_token_from_metadata` on `ExtractionConf`.
- `disagreeing_token_keys`.

**adopt/adopt/malaria.py**

- `warn_on_disagreeing_token_keys`, and its call in `update_ads_for_campaign`.

**adopt/adopt/marketing.py**

- the `isinstance` guard in `ad_ref_token` that returns `None` for anything but
  the three fly destination types.
- the same guard in `thins_its_ref_without_reading_the_mapping`
  (`study_conf.py`).
- the two `make_ref(config.name, md)` calls in `create_creative`'s
  `AppDestination` and `WebDestination` branches, which become `dotted_ref`.
- `messenger_ref` becomes `dotted_ref`; the branches in it and in
  `whatsapp_ref` that serialise the removed mode.

**inference/swoosh/inference_data.go**

- `tokenLookupKey`.
- the `Location == "metadata"` clause in `isAdTableLookup`.
- the error `getRetrieveFunc` returns for `mapping: "ad_table_lookup"` on
  `location: "variable"`.
- `entityAdOrganic`, and its branch in `adAttributionOutcome`.

**inference/swoosh/events.go**

- `entityAdOrganic` from the `classifyExtractionError` switch.

**dashboard/src/pages/StudyConfPage/forms/inferenceData/**

- `qualtricsExtraction.ts` and `QualtricsExtraction.tsx`.
- `flyExtraction.ts`, `FlyExtraction.tsx` and `flyExtraction.test.ts` are
  renamed `extraction.ts`, `Extraction.tsx` and `extraction.test.ts`;
  `SourceExtraction.tsx` renders the one component for every source.

Tests covering any of the above go with it.

## 6. Verifying

Dependencies are not shared between worktrees; a fresh checkout needs its own
`npm install` and `poetry install`.

```bash
cd dashboard  && npx tsc --noEmit && CI=true npx craco test && CI=true npx craco build
cd ../adopt   && make test-db && poetry run pytest . -q
cd ../inference && go vet ./... && go test ./...
```

- `poetry` needs Python 3.10 here; the system Python is 3.14 and the project
  requires `>=3.9,<3.11`. `poetry install` handles it.
- `make test-db` starts CockroachDB in a container and runs migrations. adopt's
  server and ad-attributions tests need it.
- `go build ./swoosh/...` fails with "build output already exists and is a
  directory". Use `go vet` and `go test` on that package.
- CRA treats warnings as errors under `CI=true`, so an unused import fails the
  production build while `tsc` passes. Run the build.
- Some adopt tests are order-dependent; run a whole file rather than one test.

Production runs `adopt v0.1.78` and `swoosh v0.1.10`, and the database is
migrated to `20260818000000` — the `ad_attributions` table and its `ref_token`
column are live.

## 7. Documentation

A dedicated pass, separate from the code commits.
`documentation/ad-attributions.md` describes the mechanism across components;
`adopt/README.md`, `dashboard/README.md` and `inference/README.md` describe
their own halves. Each describes the system as it stands.
