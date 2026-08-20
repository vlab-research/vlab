# Handover: encoded-ref attribution — built, not yet released

**Supersedes** `planning/encoded-ref-attribution-plan.md`, which was the design
handoff *into* this work. That document is still worth reading for the *why*;
this one records what was actually built, what it cost, what turned out to be
wrong in the plan, and what is left.

**Status:** all code complete and green in both repos. Nothing is released.
The remaining work is release engineering and one genuine end-to-end test that
has never been run.

**Repos and worktrees** — other agents work these concurrently. Stay in your
worktree. **Never `git stash`**: stashes are global across ~20 worktrees.

| Repo | Worktree | Branch |
|---|---|---|
| vlab | `/home/nandan/Documents/vlab-research/vlab-multi-destination` | `feature/multi-destination` |
| fly | `/home/nandan/Documents/vlab-research/fly-arrival-health` | `feature/recruitment-arrival-health` |

Both worktrees are **clean**. Do not look for uncommitted work.

---

## 1. What this feature is, in one paragraph

vlab recruits survey respondents via Meta ads, one ad per (creative, stratum)
pair. To count and optimize it must know each respondent's stratum. Historically
the whole stratum vocabulary rode inside every message's `ref`
(`creative.Static English.Age.Age.State.Bauchi.form.mnchweek`). The encoded ref
replaces that with an opaque token: adopt mints it deterministically, bakes it
into the ad's ref, freezes a row in `ad_attributions`, and swoosh recovers the
stratum variables by joining on it. fly decodes the ref locally and stamps the
token at `metadata.vt`.

---

## 2. What shipped, commit by commit

### fly — `feature/recruitment-arrival-health` (PR #150 open)

| Commit | What | Whose |
|---|---|---|
| `020498a6` | ad-id capture and exposure | pre-existing |
| `37e1e06e` | WhatsApp entry gate accepts percent-encoded metadata | pre-existing |
| `341be39a` | arrival-health metrics, alerts, **the encoded-ref decoder**, `RefDecodeError` | pre-existing |
| `9c0ef861` | `getMetadata` owns the `vt` key | code pre-existed uncommitted; this session ran the suite and committed it |
| `0f848c8a` | docs: the encoded ref, and why fly owns `vt` | this session |

**PR:** https://github.com/vlab-research/fly/pull/150 → `main`.
Branch is 1 commit behind main (`829d5e57`, message-worker replicas) and merges
clean.

### vlab — `feature/multi-destination` (no PR yet)

Pre-existing when this session began, **correct, do not rework**:

- `9bd5ac8e` — the **encoder**: `ref_encoding.py` (`mint_ref_token`,
  `encode_recruitment_ref`), golden vectors, `RefMode` on the three fly
  destinations, mode-aware `messenger_ref`/`whatsapp_ref`,
  `assert_ref_tokens_unique`.
- `0db19f14` — **persistence**: the `ref_token` migration, `campaign_queries`
  reads/writes it, CSV export carries it.

Built this session:

| Commit | What |
|---|---|
| `770eba18` | swoosh joins on `ref_token` via the `mapping` conf field |
| `b3891751` | Python `mapping` field + config-time checks |
| `08834216` | dashboard: ad-derived variable is a mapping, not a location |
| `5e243c44` | a lookup is only valid on a metadata read |
| `bc734c2f` | docs across `documentation/`, three app READMEs, the rollout plan |
| `05cc6deb` | the original design plan, committed |
| `f1c1f78c` | removed the `location: "ad"` validation (see §5) |

---

## 3. The design, as built

### The `mapping` field — the one new concept

`ExtractionConf` gains `mapping`:

- `"raw"` (and `""`, the default) — the value read IS the answer. Every conf
  ever written keeps meaning what it meant.
- `"ad_table_lookup"` — the value read is an opaque token; the answer is a
  stratum variable off the frozen `ad_attributions` row it identifies.

`location` is unchanged (`metadata` | `variable`). **There is no `"ad"`
location** — the token lives in metadata, so reading it is an ordinary metadata
read. The old `location: "ad"` joined on `ad_id` and is gone.

```
{location: "metadata", key: "vt", mapping: "ad_table_lookup", name: "gender"}

  metadata["vt"]             -> the token        (key = WHERE TO READ)
  attributions.ByRefToken[…] -> the frozen row   (the only automatic step)
  row.Metadata["gender"]     -> "women"          (name = WHICH stratum var)
```

`name` does double duty for a lookup: output variable name **and** the key into
the frozen row. That is the one constraint the design carries.

### The wire format (cross-repo contract)

```
r.<base64url(v1 | len(shortcode) | shortcode | token)>
```

Length-prefixed, **not delimited** — a delimiter is a character a shortcode
might contain, and that failure is a silent mis-route. Length is in **bytes**;
UTF-8 is variable width. Pinned by golden vectors in
`adopt/adopt/test_ref_encoding.py`. **If a change makes them fail, do NOT
regenerate them — bump `ENCODED_REF_VERSION`.** Verified byte-for-byte against
fly's shipped `decodeRecruitmentRef` on 2026-08-19, all five vectors including a
multi-byte shortcode.

---

## 4. Invariants — do not break these

- **No runtime mechanism selection.** The mechanism is declared in the conf and
  fixed at config time. Never inspect an event to choose between `ad_id` and
  `ref_token`. A token that misses is `unmapped`, never a retry against `ad_id`
  — a fallback makes a real miss indistinguishable from a mechanism switch.
- **No `ByAdID` index.** `AdAttributions` has exactly one index, `ByRefToken`.
  Adding a second is how runtime selection creeps back in. `ad_id` stays on the
  row and on the event for monitoring; fly's recruitment-health alerting gates
  on its presence.
- **The token is unquoted before joining.** Metadata values are JSON, so the
  token arrives as `"a1b2c3d4e5"` while `ref_token` comes out of a text column
  bare. `metadataToken` does the unquoting. Joining raw bytes misses every
  time, on a value that looks right in every log line.
- **fly owns `vt`.** `delete md.vt` is unconditional and **before** the decode
  branch. The case that matters is the one where the branch does *not* run: a
  dotted ref `creative.X.vt.injected.form.Y` sets `md.vt` via `_group`, and with
  no `md.r` nothing overwrites it. Pinned by ``owns `vt`: a dotted ref cannot
  inject a join key``.
- **A lookup is only valid on `location: "metadata"`.** Rejected in pydantic and
  refused by `getRetrieveFunc`. swoosh reads a lookup conf's `key` as the
  declaration of where the token lives, so one stray `variable` conf would have
  every respondent classified against the wrong key — and no token reads as
  organic, which does not alarm.
- **The token is deterministic** — `mint_ref_token(study_id, stratum_id,
  creative_name, destination_name)`. The ref is part of the creative and
  reconciliation compares creatives, so a random token rewrites every ad every
  run.
- **`ad_table_lookup` is for new studies only.** swoosh recomputes all history
  every run, so swapping an existing study's confs re-attributes its whole
  back-catalogue through a path its events cannot satisfy.
- **`ad_attributions` is append-only**, `ON CONFLICT DO NOTHING`. Frozen at
  creation. Never add a path that refreshes `metadata`.
- **A NULL `ref_token` is normal** — that ad's destination is not in
  `ref_mode: "encoded"`. Loaded but not indexed, and it must never land under
  `""`, where every tokenless respondent would match it.

---

## 5. Where the plan was wrong, or where we diverged

Read these before trusting the old plan document.

1. **`location: "ad"` validation was built, then removed.** The plan said
   "either reject it or migrate it". It was rejected in pydantic and named
   explicitly in `getRetrieveFunc` — then the user confirmed `location: "ad"`
   **was never live in any study**, so validating it was dead code. Both paths
   and their tests were removed in `f1c1f78c`. It is now just an unknown
   location and gets the same error a typo does. **Do not re-add this.**
2. **A hole the plan did not anticipate:** `variable` + `ad_table_lookup`. Found
   while reworking the dashboard form. Closed in `5e243c44` — see the invariant
   above.
3. **`AdAttributions` is a struct, not a bare map.** The plan wrote
   `attributions.ByRefToken[token]` at call sites, so it is a one-field struct
   with a `Len()` helper. Every call site says out loud which key it joined on.
4. **The multi-destination env gate is gone.** `ADOPT_ENABLE_MULTI_DESTINATION`,
   `multi_destination_enabled()` and the `multi_destination_must_be_enabled`
   validator were removed on 2026-08-20 at the user's direction, along with the
   three tests that pinned them. The measured asymmetry they encoded is still
   true and now lives in `FlyMultiDestination`'s docstring, `adopt/README.md`,
   `documentation/multi-destination-ads.md` §4 and the dashboard form copy: the
   Messenger arm is measured, the WhatsApp arm is inferred by symmetry and has
   never been observed. §4.5's result log is still empty and is still the thing
   that settles it.

5. **The `vt` fix was not authored this session.** It was sitting uncommitted in
   the fly worktree; the plan listed it under "Uncommitted and CORRECT (commit
   it)". This session ran the suite and committed it.

---

## 6. What is left

### 6a. Merge and release — the ordering is a hard constraint

**fly must be in production before any ad emits an encoded ref.** If an encoded
ref reaches today's production replybot (`v0.0.218`, verified to contain no
`decodeRecruitmentRef`), `r.<base64url>` dot-splits to `md.r` with no `md.form`
and every arrival lands in `FALLBACK_FORM` (`305`) — a real survey belonging to
someone else. That is the VIR-19 shape, and it is exactly what this feature
exists to prevent.

Safe sequence:

1. Merge fly PR #150, tag replybot, deploy. **Near-no-op**: the decode branch
   only fires on `md.r`, and no ad emits one yet.
2. Cut a new `vlab-migrations` image and get it applied (see 6b).
3. Merge vlab, deploy adopt + swoosh.
4. **Opt one staging study in** — the real end-to-end test (see 6c).
5. Only then prod.

### 6b. The migrations image is two migrations stale — and staging cannot run it

vlab migrations are **not** applied by hand. The SQL ships inside
`ghcr.io/vlab-research/vlab-migrations:<tag>` (built from `devops/migrations/`)
and runs as a Helm **pre-upgrade hook** (`devops/helm/templates/migrations.yaml`,
weight `-10`, `backoffLimit: 0` so a failure aborts `helm upgrade` before pods
roll). That hook is what protects the ordering below.

Two problems found on 2026-08-20:

- **`v0.1.0` — what `toixo-prod.yaml` pins — contains migrations only through
  `20260718000000`.** Missing `20260816000000_add_ad_attributions` (which
  *creates the table*) and `20260818000000_..._ref_token`. Unless someone applied
  them by hand, **prod has no `ad_attributions` table at all**. Verify before
  assuming.
- **`toixo-staging.yaml` has no `migrations:` block**, and the chart's
  `values.yaml` has no default — only `toixo-prod.yaml` sets one. The hook would
  template an empty image reference. Staging cannot run migrations until this is
  added.

```bash
make release SERVICE=vlab-migrations VERSION=v0.2.0
# then add to devops/values/toixo-staging.yaml:
#   migrations: {image: ghcr.io/vlab-research/vlab-migrations, tag: v0.2.0}
#   plus the db: host/port/name/sslmode the hook templates from
# then helm upgrade staging
```

**Why the ordering matters:** `GetAdAttributions` selects `ref_token`
unconditionally for **every** study, and the error path is fatal to the run
(`swooshStudy` returns err → `recordRunOutcome` error). Deploy swoosh against a
DB without the column and every study's inference run fails, not just encoded
ones. The pre-upgrade hook prevents this — do not work around it.

### 6c. Nothing has run end to end

Every layer is unit- and integration-tested, and the golden vectors match across
repos. But the full path has **never** carried a real respondent:

```
adopt mints token -> ad created on Meta -> respondent clicks
  -> fly decodes -> metadata.vt -> swoosh joins -> inference_data
```

No study sets `ref_mode: "encoded"` or declares an `ad_table_lookup` conf, so
the feature is inert today. That is the safety property *and* the gap. The UAT
is: opt one staging study in, run one real arrival through, confirm the variable
lands in `inference_data`.

### 6d. The multi-destination stack

`feature/multi-destination` is 28 commits ahead of main and carries far more
than this work: click-to-WhatsApp destinations, adset `promoted_object`, the
CTWA ref grammar, `FlyMultiDestination`, shortcode-only Messenger refs, the
dashboard forms. Releasing the encoded ref means merging all of it.

It merges **live**: both `type: "whatsapp"` and `type: "multi"` destinations are
configurable the moment it lands. The env-var gate that once held multi shut was
removed deliberately (see §5.5), so the WhatsApp arm's unverified status is now
carried by documentation and by watching the first study that uses it, not by
the type refusing to construct.

`planning/multi-destination-rollout.md` lists three blockers. **Blocker 2 (fly
never stamps an id) is closed by this work** and the document has been updated
to say so, including why ad_id could never have closed it alone. The other two
are open and are measurement/decision, not code:

1. the WhatsApp arm has never been observed end to end — §4.5 result log in
   `documentation/multi-destination-ads.md` is still empty, needs a CTWA probe
   run
2. the `CONVERSATIONS` optimization-goal conflict on the Virtual Lab Page

Neither blocks merging with multi gated off.

---

## 7. The `conversation-identity` collision

fly's `feature/conversation-identity` (actively developed; 9 commits in the two
days to 2026-08-18) collides with `feature/recruitment-arrival-health`. Both
branched from `798976ea`; conversation-identity has none of the ad-id work.

**Verified: this session's two commits added zero new conflicts** — the conflict
set computed from `341be39a` and from `HEAD` is byte-identical.

7 files, 20 hunks:

| Hunks | File |
|---|---|
| 7 | `documentation/referral-form-resolution.md` |
| 4 | `replybot/README.md` |
| 4 | `dashboard-server/queries/responses/response.test.js` |
| 2 | `replybot/lib/event-normalizer.js` |
| 1 | `replybot/lib/typewheels/utils.js` — **only the `module.exports` list** |
| 1 | `replybot/lib/typewheels/utils.test.js` |
| 1 | `devops/sql-exporter/templates/configmap.yaml` |

`getMetadata` merges cleanly: both versions call `event.source.account_id` and
`eventPlatform(event)` at the same points. `_decodeToken`, `delete md.vt`, the
decode branch and `delete md.ad_id` all survive the auto-merge intact (verified
against the trial-merge tree). conversation-identity hardens `eventPlatform`
(`STRICT_EVENT_PLATFORM`, `PLATFORM_GUESSED_TAG`) — compatible.

Recommendation was **arrival-health first**: it is the critical path, it is a
near-no-op deploy, conversation-identity carries 4 migrations and a change to
conversation *keying* that deserves to ship alone, and the conflict lands on the
branch whose author is actively in those files.

Compute the conflict set without touching a worktree:

```bash
git merge-tree --write-tree --name-only HEAD feature/conversation-identity
```

---

## 8. Test commands and expected results

| Suite | Command | Expected |
|---|---|---|
| replybot | `npm test` in `fly-arrival-health/replybot` | **521 passing** |
| inference (Go) | `go test ./... -p 1` in `inference/` | all ok; DB tests need `make test-db` |
| adopt (Python) | `poetry run pytest adopt/ -q` | **697 passed, 1 skipped** |
| dashboard | `CI=true npx craco test --watchAll=false` | **142 passed**; `npx tsc --noEmit` clean |

The Go DB tests use `postgres://root@localhost:5433/test` (container
`vlab-recruitment-test`). `make test-db` in `inference/` rebuilds it — note this
**stops and removes a shared container** other worktrees may be using.

Cross-repo contract check:

```bash
# run vlab's golden vectors through fly's decoder
cd fly-arrival-health/replybot && node -e "
const u = require('./lib/typewheels/utils');
console.log(u.decodeRecruitmentRef('AQhtbmNod2Vla14c0ufC'));  // {form:'mnchweek', token:'5e1cd2e7c2'}
"
```

---

## 9. Read these before touching anything

Per the repo's documentation-first protocol, and all updated by this work:

- `documentation/ad-attributions.md` — the whole join, both sides
- `documentation/multi-destination-ads.md`
- `inference/README.md`, `adopt/README.md`, `dashboard/README.md`
- fly: `documentation/referral-form-resolution.md` § "The encoded ref",
  `documentation/recruitment-arrival-health.md`, `replybot/README.md`
- `planning/encoded-ref-attribution-plan.md` — the original design, with §5
  above as errata
