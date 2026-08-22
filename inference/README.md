# Inference Data Collection System

The inference system collects survey responses and event data from external sources and stores them in PostgreSQL for analysis and optimization.

## Architecture Overview

The system consists of three main components:

### 1. Connectors (Go binaries)

Located in `sources/`, each connector fetches data from a specific external API and writes events to the database.

**Connector flow:**

```
CronJob trigger
    ↓
Binary main() calls connector.LoadEvents(...)
    ↓
GetStudyConfs() → (query for active studies + credentials)
    ↓
For each study:
  - LastEvent() → (get pagination token)
  - Handler() → (fetch data from external API via channel)
  - WriteEvents() → (insert to inference_data_events table)
```

**Active Study Determination:**

Studies must satisfy ALL of these conditions to be "active":

1. **Date window**: `study_state.start_date < NOW() < study_state.end_date`
   - Dates come from the study's `recruitment` config in `study_confs` table
   - The `study_state` view extracts these as real timestamp columns

2. **Has data source config**: A `study_confs` row with `conf_type = 'data_sources'` must exist
   - This config is a JSON array of source definitions
   - Each source includes a `credentials_key` to identify which credential to use

3. **Credentials exist**: The referenced credential must exist in the `credentials` table
   - Lookup is by `(user_id, entity, key)` where entity is the data source type (e.g., "alchemer")
   - **If missing, the study is silently skipped** (see risks below)

**Available Connectors:**

- `alchemer/` — Alchemer survey platform
- `fly/` — Fly.io survey platform (usually Typeform via integration)
- `typeform/` — Typeform survey platform
- `qualtrics/` — Qualtrics survey platform
- `literacy-data-api/` — Custom internal literacy data API
- `tarot/` — Custom data source (TBD)

### 2. Swoosh (Aggregator)

Located in `swoosh/`, this job runs every hour to aggregate raw inference events into structured data.

**Swoosh flow:**

```
GetActiveStudies() → (studies where start_date < NOW < end_date + 7 days)
    ↓
For each study:
  - GetEvents() → (fetch all raw events from inference_data_events)
  - Reduce() → (aggregate by user and variable using mapping config)
  - WriteInferenceData() → (insert to inference_data table)
```

**Why 7-day lookback?** Studies that ended recently may still have events to process. The 7-day window ensures all data is captured before final aggregation.

### 3. Data Storage

**`study_confs` table** — All study configurations as JSON:

| conf_type | Purpose | Schema | 
|-----------|---------|--------|
| `recruitment` | Study date window, budgets, incentives | `{start_date, end_date, opt_budget, incentive_per_respondent, ...}` |
| `data_sources` | External data sources to collect from | `[{name, source, credentials_key, config}, ...]` |
| `inference_data` | Variable mapping (how to aggregate raw events) | `{variables: {var_name: {source: "...", key: "..."}, ...}}` |
| `general` | Study name, optimization goal, etc. | `{name, objective, opt_window, ...}` |
| `strata` | Audience segments for optimization | `[{id, name, quota, audiences, creatives, ...}, ...]` |

**`inference_data_events` table** — Raw events from external sources:

| Column | Type | Purpose |
|--------|------|---------|
| study_id | UUID | Which study |
| source_name | VARCHAR | Which source config (e.g., "A1", "B2") |
| timestamp | TIMESTAMP | When the event occurred |
| idx | INT | Sequence number (for pagination resumption) |
| pagination | VARCHAR | API pagination token (for resuming fetches) |
| data | JSON | Full event data (user, metadata, answers) |

**`inference_data` table** — Aggregated data per user:

| Column | Type | Purpose |
|--------|------|---------|
| study_id | UUID | Which study |
| user_id | VARCHAR | Respondent ID |
| variable | VARCHAR | Variable name |
| value_type | VARCHAR | Type hint |
| value | JSON | Aggregated value |
| timestamp | TIMESTAMP | Latest update |

**`study_state` view** — Convenience view for active study queries:

Extracts date fields from `study_confs` with `conf_type = 'recruitment'` for easy filtering:

```sql
SELECT id, user_id, name,
       (conf->>'start_date')::TIMESTAMP as start_date,
       (conf->>'end_date')::TIMESTAMP as end_date,
       ...
FROM study_confs
WHERE conf_type = 'recruitment'
  AND ROW_NUMBER() ... = 1  -- most recent only
```

## Ad attribution

vlab creates exactly one ad per (creative, stratum) pair, so an ad already
determines the stratum it recruits for. The Python `adopt` service freezes that
fact at ad-creation time into an `ad_attributions` row (see
`documentation/ad-attributions.md` for that half). The inference side is the
read side: an event carries an opaque token identifying the ad that recruited
its respondent, and swoosh resolves stratum variables by joining on that token
— instead of parsing them out of the dotted `ref` string that used to travel
inside every message.

### The join key is `ref_token`, not `ad_id`

Both are opaque ad identifiers resolving to the same frozen row; they differ
only in the carrier.

`ad_id` rides Meta's referral webhook, which Meta sends for only ~31% of
Messenger ad entrants — the other 69% could never be joined. `ref_token` rides
the ref itself, a carrier vlab authors, so it reaches essentially everyone. The
token is minted deterministically from `(study_id, stratum_id, creative_name,
destination_name)` and travels inside the encoded ref; fly decodes it locally
and stamps it at `metadata.vt`.

`AdID` and `AdNetwork` are still on `InferenceDataEvent` and `ad_id` is still on
the row — fly's recruitment-health alerting gates on ad_id presence, and a
platform that some day needs an id-carrier join could have one back in exactly
this shape. **But nothing joins on them.** `AdAttributions` has one index,
`ByRefToken`, and deliberately no `ByAdID`.

### The `mapping` field

`ExtractionConf` carries one field that says what to do with the value read from
its `location`:

| `mapping` | Meaning |
|---|---|
| `""` / `"raw"` | the value read IS the answer. The default, so every conf written before the field existed keeps meaning what it meant. |
| `"ad_table_lookup"` | the value read is an opaque token; the answer is a stratum variable off the frozen row that token identifies. |

`location` is unchanged (`metadata` \| `variable`). There is no `"ad"` location
and there never really was one — the token lives in metadata, so reading it is
an ordinary metadata read. What makes a variable ad-derived is the mapping. The
old `location: "ad"` is **removed**. It was never live in any study, so nothing
migrates and nothing validates it away: `getRetrieveFunc` simply has no case for
it, and it falls through to the same unknown-location error any typo gets.

Both other fields are contextual to the mapping, which is the one genuinely
confusing part:

```
{location: "metadata", key: "vt", mapping: "ad_table_lookup", name: "gender"}

  metadata["vt"]                -> the token        (key = WHERE TO READ)
  attributions.ByRefToken[…]    -> the frozen row   (the only automatic step)
  row.Metadata["gender"]        -> "women"          (name = which stratum var)
```

- **`key`** addresses the token, never the stratum variable. It is never
  hardcoded: fly stamps `vt` by convention and the conf says `key: "vt"` to
  match, so a platform surfacing the token elsewhere just declares that key.
- **`name`** is the output variable name *and* the key into the frozen row. It
  does double duty because you name the output after the stratum variable it
  pulls anyway. This is the one constraint the design carries.

A lookup is valid only on `location: "metadata"`. The combination with
`"variable"` is rejected both at config time and in `getRetrieveFunc`, because
swoosh reads a lookup conf's `key` as the declaration of where the token lives
— one stray conf would otherwise have every respondent in the study classified
against the wrong metadata key.

### No runtime mechanism selection, and no fallback

The mechanism is a property of the study's conf, fixed at config time. swoosh
never inspects an event to decide whether to use `ad_id` or `ref_token`, and a
token that matches no row is `unmapped` — never a quiet retry against `ad_id`.

A runtime choice would make a genuine miss indistinguishable from a study
part-way through switching mechanisms, and every debugging session an
archaeology exercise. It is also why `ad_table_lookup` is for **new studies
only**: swoosh recomputes a study's entire history on every run, so swapping an
existing study's confs over would retroactively re-attribute its whole
back-catalogue through a path its events cannot satisfy (rows written before
the study's ads carried an encoded ref have no token and are never backfilled).
Every historical respondent would extract nothing, match no stratum, and vanish
from the counts.

### The token is unquoted before joining

Metadata values are JSON, so the token arrives as a quoted JSON string
(`"a1b2c3d4e5"`) while `ad_attributions.ref_token` is scanned out of a text
column bare. Joining the raw bytes would miss every single time, on a value that
looks correct in every log line it appears in. `metadataToken`
(`swoosh/inference_data.go`) does the unquoting; a value that is not a JSON
string is treated as no token at all.

### Where the database touch lives

`GetAdAttributions` (`swoosh/ad_attributions.go`) runs once per study in
`swooshStudy`, before `Reduce`. `Reduce` takes the mapping as plain data and
`retrieveFromMetadata` closes over it. This is deliberate: `RetrieveFunc` has no
context and no error and runs once per event per conf, so a query inside it
would be one query per response. The load is also per-study, so a foreign
study's token misses the lookup rather than importing that study's strata —
and keeping the lookup out of `Reduce` is what keeps `Reduce` pure and
unit-testable against a fake mapping.

A row whose `ref_token` is NULL is loaded but not indexed. NULL is the normal
case and means something: that ad's ref carries no token because its destination
is not in `ref_mode: "encoded"`. It has no join key, so there is nothing to
index it under — and critically it must not land under `""`, where every
tokenless respondent would match it.

### Only the unmappable is reported

`adAttributionOutcome` (`swoosh/inference_data.go`) asks one question of each
event: could this respondent be attributed, and should they have been.

| Outcome | Meaning | Handling |
|---|---|---|
| attributed | token present, mapping row found | normal, no event |
| no ad provenance | no token on the event | expected; **no event at all** |
| unmapped | token present, no mapping row | always a bug; counted at severity `error` |

Classification happens once per *event*, not per conf, so one miss is not
multiplied by the number of lookup confs a study declares (see
`tokenLookupKey`). `classifyExtractionError` (`swoosh/events.go`) maps
`unmapped` to `error` severity, alongside the existing `source=`-prefixed
warnings. Its details name the mechanism (`ref_token`) and the key it read, so a
miss is diagnosable from the row.

There used to be a third outcome, `ad=organic`, warning on any event with no
token. It classified by mechanism state rather than by outcome, and it needed an
explicit "must not alarm" carve-out — which is the tell that an expected result
had been put on an error surface. Worse, a study switching to the encoded ref
keeps its inline confs alongside the new lookup ones, so both eras attribute;
but every pre-switch respondent has no token, and swoosh recomputes all history
every run, so it reported the entire back-catalogue as unattributed, forever,
falsely. (Compare the 52,090-row `source=Fly` false alarm in
`planning/swoosh-config-reconciliation.md`.) What it nominally measured — the
share of arrivals with no ad provenance — is a rate needing a denominator an
error list has not got, and is tracked as VIR-32.

Unmapped is self-healing: swoosh recomputes everything each run, so inserting
the missing `ad_attributions` row retroactively fixes prior runs, and the
dashboard's recency window ages the stale error out on its own.

`tokenLookupKey` takes the *first* lookup conf's key when a source declares
several. All of them are supposed to agree — one respondent has one token in one
place — and adopt's `disagreeing_token_keys` warns at config time when they do
not. swoosh guesses rather than refusing because it recomputes whole studies
unattended, and refusing to classify would cost a study its counts over a conf
problem no run can fix from the inside.

### Tests

- `swoosh/ad_attributions_test.go` — the pure outcome and extraction tests,
  plus DB-backed `swooshStudy` tests (needs `make test-db`).
- The ad-attribution section of `sources/fly/main_test.go`.

See `documentation/ad-attributions.md` and
`planning/encoded-ref-attribution-plan.md` for more detail, including the write
side in `adopt`.

## Execution Model

### Kubernetes CronJobs

All collection jobs run as CronJobs scheduled from Helm charts:

| Job | Schedule | Image | Connector |
|-----|----------|-------|-----------|
| literacy-data-api | `10 * * * *` (hourly, min 10) | `vlabresearch/source-literacy-data-api` | Literacy API |
| fly | (no CronJob; part of other pipeline) | - | - |
| typeform | (no CronJob; part of other pipeline) | - | - |
| alchemer | (no CronJob; part of other pipeline) | - | - |
| swoosh | `30 * * * *` (hourly, min 30) | `vlabresearch/swoosh` | Aggregator |
| adopt-ads | `30 */4 * * *` (every 4 hrs) | `vlabresearch/adopt:inference-data` | Facebook optimization |
| adopt-recruitment-data | `10 */4 * * *` (every 4 hrs) | `vlabresearch/adopt:inference-data` | Recruitment reporting |
| adopt-audience | `50 */4 * * *` (every 4 hrs) | `vlabresearch/adopt:inference-data` | Audience management |

**Concurrency Policy**: All use `concurrencyPolicy: Forbid`, preventing overlapping runs.

### Pagination Strategy

Connectors resume from where they left off using pagination tokens:

1. **Call `LastEvent(pool, source, orderColumn)`**
   - Queries the most recent event by `orderColumn` (e.g., "timestamp" or "idx")
   - Returns the full event data including the `pagination` field

2. **Pass to `Handler(source, lastEvent)`**
   - Handler extracts `lastEvent.Pagination` (the API's pagination token)
   - Passes it to the external API to resume fetching from that point

3. **Store new pagination token**
   - Each event emitted by Handler includes a `pagination` field
   - WriteEvents() stores this in the database for next run

**Example**: Alchemer stores `date_submitted` as pagination token:
```go
token := lastEvent.Pagination  // e.g., "2024-01-15 10:30:00"
// Call Alchemer API with filter: "date_submitted > token"
// Emit events with pagination = item.DateSubmitted
```

This approach assumes:
- APIs support resumable pagination (most do)
- Pagination tokens remain valid across runs (usually true)
- No data is lost or duplicated (depends on API consistency)

## Known Risks and Limitations

### 1. Silent Credential Failure

If a study's data source config references a credential that doesn't exist, the study is silently skipped with no error. No warnings are logged.

**Impact**: Silent data collection failures. User won't know credentials were missing until checking the database or dashboards.

**Mitigation**: Validate credentials proactively in the query, not just via JOIN filter.

### 2. Time Zone Assumptions

All date comparisons use `NOW()` in the database, which is **assumed to be UTC**. If the server time zone is not UTC, date filtering may fail.

**Impact**: Studies may be incorrectly included or excluded based on server timezone.

**Mitigation**: Ensure PostgreSQL is configured with `timezone = 'UTC'`.

### 3. Pagination Token Durability

If an API's pagination token format changes or the token expires, the connector cannot resume and must either:
- Fail (current behavior: fatal error)
- Restart from the beginning (risk: duplicate data)
- Skip data (risk: missing data)

**Impact**: Long-running studies risk data loss or duplication if APIs change.

**Mitigation**: Implement token validation and graceful fallback to restart if token is invalid.

### 4. No Per-Study Error Isolation (Go System)

If one study's fetch fails, the entire connector binary exits with a fatal error. Other studies in the same batch won't be processed.

**Impact**: One misconfigured study blocks data collection for all studies that run in the same CronJob.

**Note**: The Python `adopt/` system handles this better by catching per-study errors.

**Mitigation**: Catch errors per-study, log context, and continue to next study.

### 5. Exclusive End Date Boundary

The query uses `end_date > NOW()`, which excludes data from the exact moment the study ends. A study ending at `2024-01-31T23:59:59Z` loses the last second if a CronJob runs at `2024-02-01T00:00:00Z`.

**Impact**: Negligible (seconds) but strict students might complain.

**Mitigation**: Use `end_date >= NOW()` or adjust comparison logic.

## Configuration

### Environment Variables

**All connectors:**
- `PG_URL` — PostgreSQL connection string (required, e.g., `postgres://user:pass@host:5432/vlab`)

**Connector-specific:**
- `ALCHEMER_BASE_URL` — Alchemer API base URL
- `ALCHEMER_PAGE_SIZE` — Results per page
- `FLY_BASE_URL` — Fly API base URL
- `FLY_PAGE_SIZE` — Results per page
- `TYPEFORM_BASE_URL` — Typeform API base URL
- `TYPEFORM_KEY` — Typeform API key
- `TYPEFORM_PAGE_SIZE` — Results per page
- (others as needed for each source)

All loaded via `github.com/caarlos0/env/v6` — supports `.env` files or environment variables.

### Database Migrations

Schemas defined in:
- `/devops/migrations/20230322111807_init.up.sql` — Main tables and views
- `/devops/migrations/initvlab/` — Seed data for development

## Building and Running

### Go Connectors

```bash
cd inference/sources/alchemer
go build -o alchemer main.go
PG_URL="postgres://..." ALCHEMER_BASE_URL="..." ALCHEMER_PAGE_SIZE=50 ./alchemer
```

### Swoosh

```bash
cd inference/swoosh
go build -o swoosh swoosh.go
PG_URL="postgres://..." ./swoosh
```

### Docker

```bash
# Build all inference images
docker build -t vlabresearch/source-alchemer inference/sources/alchemer/
docker build -t vlabresearch/swoosh inference/swoosh/

# Push to registry for Kubernetes
docker push vlabresearch/source-alchemer:latest
docker push vlabresearch/swoosh:latest
```

## Connector Interface

To implement a new data source connector:

1. **Implement the `Connector` interface** in `connector/connector.go`:
   ```go
   type Connector interface {
       Handler(source *Source, lastEvent *InferenceDataEvent) <-chan *InferenceDataEvent
   }
   ```

2. **The Handler method:**
   - Receives the `Source` (study + credentials + config)
   - Receives the last event (if any) for pagination resumption
   - Returns a channel of `InferenceDataEvent`s
   - Should emit events asynchronously (typically via a goroutine)

3. **Call `connector.LoadEvents()`** in main():
   ```go
   func main() {
       c := MyConnector{}
       c.loadEnv()
       connector.LoadEvents(c, "my_source", "idx")
   }
   ```

4. **Each event must include:**
   - `Study` — study ID (string)
   - `SourceConf` — the source config (name, source, config, credentials_key)
   - `User` — respondent info (ID + metadata)
   - `Timestamp` — when the event occurred
   - `Variable` — variable name (question ID, field name, etc.)
   - `Value` — the value (JSON)
   - `Idx` — sequence number (for ordering)
   - `Pagination` — API pagination token (for resuming)

## Testing

Run tests:

```bash
cd inference/connector
go test -v ./...
```

Test validates:
- Only active studies are returned
- Only studies with matching credentials are returned
- Latest config version is used
- Missing credentials are handled gracefully
- Event pagination and storage works

## Related Systems

- **`adopt/`** — Ad optimization and budget allocation (runs separately, also uses active study filtering)
- **`api/`** — REST API for study configuration and querying results
- **`dashboard/`** — Frontend for visualizing aggregated inference data

## Per-Study Error Isolation

The connector now includes **per-study error isolation** to prevent one study's failure from blocking other studies. If one study's data collection fails (e.g., API error, bad credentials), the error is logged with full context and the connector continues to the next study.

Implementation:
- Each study's processing is wrapped in error recovery
- Errors are logged with full context (study ID, source, operation)
- The connector continues to the next study instead of fataling
- Similar to the Python `adopt/` system, which already handles this gracefully

---

## References

- [Active Study Filtering Details](../../planning/connector-active-study-findings.md)
- Database schema: `/devops/migrations/20230322111807_init.up.sql`
- Kubernetes manifests: `/devops/helm/templates/cronjobs.yaml`
