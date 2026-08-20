# Plan: encoded-ref attribution via a `mapping` concept

**Status:** design settled through interactive discussion; implementation to be
done by a future agent. This document is the handoff — it captures the design,
the rationale, the current state of both repos, and the concrete steps.

**Repos:** two — **vlab** (`/home/nandan/Documents/vlab-research/vlab-multi-destination`,
branch `feature/multi-destination`) and **fly**
(`/home/nandan/Documents/vlab-research/fly-arrival-health`, branch
`feature/recruitment-arrival-health`). They are worked in separate worktrees.
Other agents work these repos concurrently — stay in your worktree, never
`git stash` (stashes are global across ~20 worktrees).

---

## 1. The goal

vlab recruits survey respondents via Meta ads. Each ad belongs to one **stratum**
(a segment defined by a metadata vocabulary, e.g. `gender=women, Age=25_34`).
To count and optimize, vlab must associate each respondent with their stratum's
metadata variables. There are several ways to get those variables onto a
respondent, and the study's **extraction confs** declare which way via a
`location` field.

This work adds a new attribution mechanism — the **encoded ref** — that lets a
study stop shipping its stratum vocabulary inside every message's ref, and
instead recover those variables by **joining on an opaque token**. It is the
read-side counterpart to the encoded-ref encoder already built and committed on
the vlab branch (see §4).

---

## 2. The settled design

### 2.1 The mapping concept (the one new thing)

Today an `ExtractionConf` reads a value from a `location` (`metadata` or
`variable`) and uses it as-is. We add **one new field**, `mapping`, that says
what to do with the read value:

- `mapping: "raw"` (default) — the value is the answer. Today's behaviour.
- `mapping: "ad_table_lookup"` — the value is a token; look it up in
  `ad_attributions` by token and return the stratum variable off the frozen row.

`location` is **unchanged** (`metadata` | `variable`). The token lives in
metadata, so reading it is a normal `location: "metadata"` read. `"ad"` is
**not a location** — it never was; the token is in metadata. The existing
`location: "ad"` value (from the ad-id-attribution work) is **deprecated and
removed**.

### 2.2 The two cases, side by side

```
// legacy — the value rides the ref inline
{location: "metadata", key: "gender", mapping: "raw", name: "gender"}
  ->  metadata["gender"]  ->  "women"
//      key = where to read in metadata      name = output variable name

// encoded — a token rides the ref; the value is looked up
{location: "metadata", key: "vt", mapping: "ad_table_lookup", name: "gender"}
  ->  metadata["vt"]              (key = where to read: the token)
  ->  ad_attributions[token]      (the mapping — the ONLY automatic part)
  ->  row.metadata["gender"]      (name = which stratum variable, and the output name)
  ->  "women"
```

**Field meanings:**
- `key` — where to read in metadata. For `raw`, this is the value itself; for
  `ad_table_lookup`, this is the token. (Same field, contextual to `mapping` —
  exactly as `key` is already contextual to `location` today.)
- `name` — the output variable name. For `ad_table_lookup`, **also the key into
  the frozen row's metadata** (the stratum variable to return). So for
  `ad_table_lookup`, the output is named after the stratum variable it pulls.
  This `name`-does-double-duty is the one constraint; it is acceptable because
  you name the output after the stratum variable anyway.
- `mapping` — the only new field. `raw` | `ad_table_lookup`.

### 2.3 ref_token is the join key; ad_id is deprecated as a join

`ad_attributions` is a row per created ad, frozen at ad-creation time. It
gains a `ref_token` column (already done, committed — see §4). The join uses
`ref_token`. **ad_id is deprecated as a join mechanism** — it stays captured in
the table and in fly's metadata for monitoring (the fallback-form alert gates
on ad_id presence) and could come back in the same shape if a platform ever
needs it, but it is never joined. The table holds both columns; `(network,
ad_id)` stays the primary key, `ref_token` is the join column.

**Why ref_token supersedes ad_id:** they are the same shape (opaque ad
identifier -> frozen row -> stratum metadata), differing only in the carrier.
ad_id rides Meta's referral webhook, which Meta sends for only ~31% of
Messenger ad entrants — the other 69% can't be joined. ref_token rides the ref
itself (a carrier vlab authors), so it reaches ~100%. ref_token is the superior
version; ad_id is the deprecated earlier attempt.

### 2.4 The token's metadata key is conf-declared, never hardcoded

vlab's join code never assumes the token is at `metadata["vt"]`. The conf's
`key` field declares where the token is. fly stamps `metadata.vt` (a
convention), and the conf says `key: "vt"` to match. A different platform
producing the token under a different metadata key would just declare a
different `key`. The only automatic part is `token -> ad_attributions row ->
stratum metadata`.

### 2.5 The mechanism is conf-declared, never selected at runtime

**No runtime key-sniffing.** The user was explicit: the attribution mechanism
is a property of the study conf, fixed at config time, never chosen at read
time by whichever key happens to be present. A token that misses the mapping is
an **unmapped error**, never a silent retry against ad_id. A runtime choice
would make a genuine miss indistinguishable from a mechanism switch.

### 2.6 Config-time agreement check

All `ad_table_lookup` confs under one source must share the same `key` (the
token location) — one respondent has one token, in one place. This is a
config-time validator (same style as the existing half-migration guard,
`thins_its_ref_without_reading_the_mapping`), not a structural enforcement.

---

## 3. The cross-repo contract: the encoded ref wire format

Pinned by tests on both sides. Changing it means changing both repos together
and bumping `ENCODED_REF_VERSION`.

```
r.<base64url(v1 | len(shortcode) | shortcode | token)>
```

- byte 0: version (`0x01`)
- byte 1: length of the shortcode IN BYTES (1..255)
- bytes 2..: the shortcode, UTF-8
- remainder: the opaque token (>= 1 byte), surfaced as lowercase hex

- `base64url` (unpadded) — alphabet `[A-Za-z0-9_-]`, no `.`, so it cannot
  collide with the dotted key/value grammar and passes fly's WhatsApp entry
  gate unencoded.
- length-prefixed, not delimited — a delimiter is a character a shortcode might
  contain, and that failure would be a silent mis-route.
- length in bytes, not characters — UTF-8 is variable width.
- the token is a join key into `ad_attributions`, minted deterministically from
  `(study_id, stratum_id, creative_name, destination_name)` via
  `mint_ref_token` (blake2b, 5 bytes / 40 bits, domain-separated). Determinism
  is a hard requirement: the ref is part of the creative, and reconciliation
  compares creatives, so a random token would rewrite every ad on every run.

**fly decodes locally** (`decodeRecruitmentRef` in
`replybot/lib/typewheels/utils.js`); no lookup, no shared state. fly's WhatsApp
entry gate accepts a second anchor `r.<base64url>` (`WHATSAPP_ENTRY_REF_ENCODED`
in `replybot/lib/event-normalizer.js`). On Messenger, `getMetadata` recognizes
`md.r` and decodes it into `md.form` + `md.vt`, outside the existing swallowing
try/catch — a malformed encoded ref throws `RefDecodeError` (tag `REF_DECODE`)
and the respondent lands in a visible ERROR state, not `FALLBACK_FORM`.

**Golden vectors** in `adopt/adopt/test_ref_encoding.py` were verified against
fly's shipped decoder, byte for byte (including a multi-byte shortcode). If a
change makes them fail, do NOT regenerate them to pass — bump
`ENCODED_REF_VERSION`.

---

## 4. Current state of both repos

### 4.1 vlab — `feature/multi-destination` (worktree `vlab-multi-destination`)

**Committed and CORRECT (keep):**
- `9bd5ac8e` — **the encoder**. `adopt/adopt/ref_encoding.py`
  (`mint_ref_token`, `encode_recruitment_ref`, `encoded_ref`,
  `decode_recruitment_ref`), `adopt/adopt/test_ref_encoding.py` (golden
  vectors), `adopt/adopt/study_conf.py` (`RefMode` mixin, `ref_mode` field on
  the three fly destinations: `metadata` | `shortcode` | `encoded`,
  `resolved_ref_mode`, the no-contradiction validator),
  `adopt/adopt/marketing.py` (mode-aware `messenger_ref` / `whatsapp_ref`,
  `ad_ref_token`, `assert_ref_tokens_unique`), `adopt/adopt/test_marketing.py`
  (encoded-ref integration tests). **This is the WRITE side — what the ad
  carries. It is done and correct. Do not rework it.**
- `0db19f14` — **persistence**. `devops/migrations/20260818000000_add_ad_attributions_ref_token.up.sql`
  (adds `ref_token` column, both schema paths),
  `adopt/adopt/campaign_queries.py` (writes/reads `ref_token`),
  `adopt/adopt/server/csv_export.py` (`ref_token` in the export),
  `adopt/adopt/test_ad_attributions.py` (persistence tests). **Done and
  correct. Keep.**

**Uncommitted and SUPERSEDED (discard):**
- 6 modified Go files in `inference/`:
  `inference-data/inference_data.go`, `sources/fly/main.go`,
  `swoosh/ad_attributions.go`, `swoosh/ad_attributions_test.go`,
  `swoosh/inference_data.go`, `swoosh/swoosh.go`.
  These implement a **superseded design**: a typed `RefToken` field on
  `InferenceDataEvent`, a two-index `Attributions` struct, and
  `attributionKey` runtime mechanism-selection. **Discard them**:
  `git checkout -- inference/` in the worktree. This reverts to the committed
  state, which has the **old `location: "ad"` joining on ad_id** (from the
  ad-id-attribution work that `feature/multi-destination` branched from). The
  read-side rework in §5 starts from there.

### 4.2 fly — `feature/recruitment-arrival-health` (worktree `fly-arrival-health`)

**Committed (shipped):**
- `341be39a` — arrival health metrics, alerts, the encoded ref decoder
  (`decodeRecruitmentRef`), the `r.` WhatsApp gate anchor, `getMetadata` decode
  branch, `RefDecodeError` (tag `REF_DECODE`), the `transition.js` tag-aware
  fix, `states.ad_id` migration, the `recruitment_health` collector, the two
  alerts. **Done.**

**Uncommitted and CORRECT (commit it):**
- `replybot/lib/typewheels/utils.js` + `replybot/lib/typewheels/utils.test.js`
  — the `delete md.vt` change (fly owns the `vt` metadata key, see §5.1) and
  the injection test. **Run the full suite (`npm test`), then commit.**

---

## 5. Implementation steps

### 5.1 fly — commit the `vt` ownership change (DONE, needs commit)

In `replybot/lib/typewheels/utils.js` `getMetadata`, `delete md.vt` is now
**unconditional and before** the decode branch, so a dotted ref like
`creative.Smiling.vt.injected.gender.women.form.mnchweek` cannot pre-populate
`md.vt` via `_group` (the decode branch only fires when `md.r` is present, so
without the unconditional delete a dotted `vt` pair would survive as an
author-injected join key — a silent mis-join). This mirrors how `ad_id` is
owned (`delete md.ad_id` before stamping). The test `owns vt: a dotted ref
cannot inject a join key` pins it.

**Action:** run `npm test` in `fly-arrival-health/replybot`; expect 521
passing (was 520 + 1 new). Commit on `feature/recruitment-arrival-health`:
`fix(getMetadata): own the vt metadata key, prevent dotted-ref injection`.

### 5.2 vlab — discard the superseded Go work

```
cd /home/nandan/Documents/vlab-research/vlab-multi-destination
git checkout -- inference/
```

This reverts the 6 Go files to the committed state (old `location: "ad"` /
ad_id join). Verify with `git status --short` (should be clean).

### 5.3 vlab Go — the `mapping` field and the ref_token join

**`inference/inference-data/inference_data.go`:**
- Remove the `RefToken` typed field if present (after discard it won't be).
  The token rides `User.Metadata` (key declared by the conf). Do NOT add a
  typed `RefToken` field — that was the superseded design.
- `AdID` / `AdNetwork` stay (ad_id is captured for monitoring, just not joined).
- `ExtractionConf` gains `Mapping string` (`json:"mapping,omitempty"`). Valid
  values: `""` / `"raw"` (default) | `"ad_table_lookup"`. The `Location` field
  loses `"ad"` as a valid value (deprecated/removed).

**`inference/swoosh/inference_data.go`:**
- Remove `retrieveFromAd`. Replace with mapping-aware `retrieveFromMetadata`:
  - read `e.User.Metadata[conf.Key]` (the raw value — the token for
    `ad_table_lookup`, the value for `raw`).
  - if `conf.Mapping == "ad_table_lookup"`: look up
    `attributions.ByRefToken[token]`; return `row.Metadata[conf.Name]`.
  - else: return the raw value.
  - `retrieveFromMetadata` must close over `attributions` (it already has
    access via `getRetrieveFunc`'s signature).
- `getRetrieveFunc`: switch on `location`. `"metadata"` -> the mapping-aware
  retrieveFromMetadata. `"variable"` -> retrieveFromVariable (unchanged).
  Remove the `"ad"` case.
- `adAttributionOutcome`: rework the organic/unmapped classification. For a
  study with any `ad_table_lookup` confs: the token is read from
  `metadata[key]` where `key` is the shared token key (the agreement check
  guarantees all ad_table_lookup confs share one). No token -> **organic**
  (expected). Token present, no `ByRefToken` row -> **unmapped** (always a
  bug). ad_id no longer determines this classification. The error message
  should name the mechanism (`ref_token`) and the token value, so a miss is
  diagnosable. Keep the per-event (not per-conf) classification.
- `Reduce` / `extractValue`: signatures pass `Attributions` through as today.

**`inference/swoosh/ad_attributions.go`:**
- Keep `AdAttribution` with `RefToken string` (the join column) and `AdID` /
  `Network` (captured, not joined).
- Index: `ByRefToken` (map[string]AdAttribution). The `GetAdAttributions`
  loader populates `ByRefToken` for rows whose `ref_token` is non-empty. Do
  NOT build a `ByAdID` join index — ad_id is not joined. (If you want to keep
  ad_id-as-join a one-line wire-up away, leave a comment, but don't populate
  the index — deprecation, not a parallel mechanism.)
- Remove `attributionKey` / `Attributions` two-index struct /
  `attributionMechanism` — no runtime selection. The "mechanism" is
  `mapping: "ad_table_lookup"`, declared in the conf, not inferred from the
  event.
- `GetAdAttributions` query: `SELECT ad_id, network, stratum_id, metadata,
  ref_token FROM ad_attributions WHERE study_id = $1`. (ad_id still selected —
  it's in the row for capture/monitoring.)

**`inference/sources/fly/main.go`:**
- Do NOT add `refTokenFromMetadata` or a `RefToken` field. The token rides
  `item.Metadata` into `User.Metadata` naturally — that's the whole point of
  "the token is in metadata." No connector change is needed for the token.
  `AdID` / `adFields` stay (ad_id captured).

**`inference/swoosh/ad_attributions_test.go`:**
- Rework the test factories and call sites for the mapping design. The
  existing tests assert the ad_id join behaviour — update them to assert the
  ref_token join via `metadata[key]` + `mapping: "ad_table_lookup"`. The
  organic/unmapped tests change basis (token presence, not ad_id).
- Add tests: a respondent with `metadata["vt"]` matching a `ByRefToken` row
  attributes correctly; a token that matches no row is unmapped; no token is
  organic; the frozen `name` field is what's returned off the row.

### 5.4 vlab — config-time validators

Find where `ExtractionConf` / `location` validation lives (Python study_conf or
dashboard). Add:
- **The agreement check**: all `ad_table_lookup` mapping confs under one source
  share the same `key`. Raise/warn at config time.
- **Rework the half-migration guard**
  (`thins_its_ref_without_reading_the_mapping` in `study_conf.py`): a study
  with `ref_mode: "encoded"` destinations but no `ad_table_lookup` confs has no
  attribution — warn. (The guard currently checks `include_metadata_in_ref` off
  + no `location: "ad"`; rework for `ref_mode` + `mapping`.)
- `location: "ad"` is no longer valid — any conf using it should be flagged
  (it's the deprecated ad_id join). Either reject it or migrate it to
  `location: "metadata", mapping: "ad_table_lookup"`.

### 5.5 vlab — dashboard form

The dashboard (`dashboard/src/`) has forms for extraction confs, including the
"Ad (which ad recruited them)" location option offered on fly sources only.
- Remove the `location: "ad"` option.
- Add a `mapping` field to the extraction conf form: `raw` |
  `ad_table_lookup`. Show it when `location: "metadata"`.
- The "Ad" option becomes: `location: "metadata"` + `mapping: "ad_table_lookup"`.
- The "offer on fly sources only" guard reworks: `ad_table_lookup` is offered
  where the source can produce a token (fly today; a platform that surfaces
  `vt` later opens it with no structural change). The test asserting Qualtrics
  offers no `ad` location becomes "Qualtrics offers no `ad_table_lookup`
  mapping."
- Update the frontend tests.

### 5.6 vlab — documentation

- **`documentation/ad-attributions.md`** — rewrite. Key changes: ref_token is
  the ad-derived join mechanism; ad_id is deprecated as a join but kept
  captured for monitoring/alerting and future reuse in the same shape; the
  token's metadata key is conf-declared (`key`), not hardcoded; the new
  `mapping` concept (`raw` | `ad_table_lookup`) on `ExtractionConf`; `location:
  "ad"` is removed. Note the already-built ad-id join work is **superseded by
  the stronger mechanism, not wrong** — the capture and monitoring halves
  survive, only the join half is replaced.
- **`documentation/multi-destination-ads.md`** — update §4.5 result log and any
  ad_id-as-join references.
- **`planning/multi-destination-rollout.md`** — the blocker about fly's ad-id
  half is stale (fly's ad-id capture exists at `020498a6`); revise.
- **`documentation/recruitment-arrival-health.md`** (in fly) — note the `vt`
  ownership (`delete md.vt`) if not already.

---

## 6. Testing requirements

- **fly**: `npm test` in `replybot` — expect 521 passing after the `delete
  md.vt` test. The encoded-ref decoder, the `r.` gate, `getMetadata`, and the
  injection test must all pass.
- **vlab Go**: `go test ./...` in `inference/`. The ad_attributions tests,
  extraction tests, and swoosh tests must pass with the ref_token join.
- **vlab Python**: `poetry run pytest adopt/` — the encoder tests
  (`test_ref_encoding.py`, `test_marketing.py` encoded tests) and persistence
  tests (`test_ad_attributions.py`) are committed and should stay green; add
  tests for the `mapping` field and the agreement validator.
- **vlab frontend**: the dashboard extraction conf tests, updated for `mapping`.
- **Cross-repo**: the golden vectors in `test_ref_encoding.py` are the
  contract. Optionally re-verify them against fly's decoder by running the
  vectors through `decodeRecruitmentRef` in node.

---

## 7. Invariants & gotchas

- **No runtime mechanism selection.** The mechanism is `mapping:
  "ad_table_lookup"` in the conf. Never inspect the event to decide whether to
  use ad_id or ref_token. ad_id is not joined, period.
- **`name` does double duty for `ad_table_lookup`** — it is both the output
  variable name and the key into the frozen row's metadata. The output is named
  after the stratum variable.
- **fly owns `vt`** — `delete md.vt` is unconditional and before the decode
  branch, so a dotted ref cannot inject a join key. Do not remove this.
- **The token is deterministic** — `mint_ref_token(study_id, stratum_id,
  creative_name, destination_name)`. Non-negotiable: the ref is part of the
  creative and reconciliation compares creatives.
- **`assert_ref_tokens_unique`** runs at instruction-generation time (the last
  cheap moment before ads exist on Facebook and are spending). A collision is a
  loud config error, not a silent mis-join.
- **ad_attributions is append-only** — `ON CONFLICT DO NOTHING`. The frozen
  blob (and ref_token) are never overwritten. ref_token is frozen like
  everything else.
- **Legacy dotted refs are permanent.** Every existing study keeps
  `creative.X.form.Y` forever; the encoded ref is opt-in per study via
  `ref_mode: "encoded"` on the destination. `mapping: "raw"` is the default.
- **No fallback between attribution mechanisms.** A token that misses is an
  unmapped error, never a retry against ad_id. (This is why ad_id-as-join is
  removed, not kept as a secondary.)
- **The ref_mode on destinations (write side) and the mapping on extraction
  confs (read side) are orthogonal.** A study can emit full refs and declare
  `mapping: "raw"`; a study can emit encoded refs and declare
  `ad_table_lookup`. The half-migration guard catches the incoherent combos.
- **Never `git stash`** — stashes are global across ~20 worktrees.
- **Before any work**, read `documentation/ad-attributions.md`,
  `documentation/multi-destination-ads.md`, `adopt/README.md`, and
  `inference/README.md` (per the repo's documentation-first protocol).

---

## 8. What is deliberately out of scope

- Writing ad_attributions rows at instruction-generation time (before the Graph
  call). ref_token is known before ad creation (deterministic), so this is
  *possible*, but it's a write-path change. Keep the current path: write the
  row after `created_id` returns, with `ref_token` included. The "write
  earlier" option can be revisited separately.
- ad_id-as-join. Deprecated. The column and capture stay; the join goes. If a
  platform ever needs it, it comes back in the same shape.
- Cross-checking ad_id against ref_token when both are present (a "must agree"
  error). Not built — ad_id is not joined, so there's no second result to
  disagree with. ad_id is monitored separately.
- Migrating existing studies to encoded refs. New studies only — adopting the
  encoded ref changes the creative, which rewrites a study's ads.
