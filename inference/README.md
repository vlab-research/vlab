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

## Ad-ID attribution

vlab creates exactly one ad per (creative, stratum) pair, so an ad's id already
determines the stratum it recruits for. The Python `adopt` service freezes that
fact at ad-creation time into an `ad_attributions` row (see
`documentation/ad-attributions.md` for that half). The inference side is the
read side: an event carries the id of the ad that recruited its respondent, and
swoosh resolves stratum variables by joining on that id — instead of parsing
them out of the dotted `ref` string that used to travel inside every message.

### The event fields

`InferenceDataEvent` (`inference-data/inference_data.go`) carries `AdID` and
`AdNetwork` as first-class typed fields, not reserved keys inside
`User.Metadata`. A map key would be a fly-shaped convention that every future
connector has to imitate with nothing enforcing it — the same shape of mistake
as the dotted ref, which was a convention smuggled inside an untyped blob. The
field is the contract; each source works out how to meet it.

No migration was needed to add them: `inference_data_events` stores the whole
event as one JSON blob in its `data` column, and both fields are `omitempty`,
so existing rows are byte-identical to what they were before the fields
existed.

### `AdNetwork` is the ad network, not the messaging channel

Messenger ads and WhatsApp ads are both Meta ads sharing one id namespace, so
both map to `NetworkFacebook` ("facebook"). `ad_attributions` is keyed
`(network, ad_id)`, so getting this backwards makes every lookup miss — and a
miss does not error, it attributes the respondent to no stratum. The fly
connector (`sources/fly/main.go`) derives the network from fly's `platform`
metadata key via `adNetworkForPlatform`/`platformFromMetadata`; an
unrecognised platform yields `""` rather than a guess.

### `location: "ad"`

A third value alongside `"variable"` and `"metadata"` in swoosh's
`getRetrieveFunc` (`swoosh/inference_data.go`). The user declares these confs
with the same `ExtractionConf` shape as any other location — vlab derives
nothing.

There is deliberately **no fallback to `location: "metadata"`, and adding one
would be a bug**: swoosh recomputes a study's entire history on every run, so a
fallback would let someone swap an existing study's conf and silently
re-attribute its whole back-catalogue through a path its events cannot
satisfy (pre-ad-id rows carry no ad id and are never backfilled).
`location: "ad"` is for new studies only; existing studies keep `"metadata"`
and full refs permanently.

### Where the database touch lives

`GetAdAttributions` (`swoosh/ad_attributions.go`) runs once per study in
`swooshStudy`, before `Reduce`. `Reduce` takes the mapping as plain data and
`retrieveFromAd` closes over it. This is deliberate: `RetrieveFunc` has no
context and no error and runs once per event per conf, so a query inside it
would be one query per response. The load is also per-study, so a foreign
study's ad id misses the lookup rather than importing that study's strata —
and keeping the lookup out of `Reduce` is what keeps `Reduce` pure and
unit-testable against a fake map.

### The three-way split

`adAttributionOutcome` (`swoosh/inference_data.go`) classifies each event
against the study's mapping:

| Outcome | Meaning | Handling |
|---|---|---|
| attributed | ad id present, mapping row found | normal, no event |
| organic | no ad id on the event | expected; counted as a warning, does not alarm |
| unmapped | ad id present, no mapping row | always a bug; counted at severity `error` |

Classification happens once per *event*, not per conf, so one organic arrival
is not multiplied by the number of ad confs a study declares (see
`hasAdConf`). `classifyExtractionError` (`swoosh/events.go`) maps `unmapped` to
`error` severity and `organic` to `warning`, alongside the existing
`source=`-prefixed warnings.

Unmapped is self-healing: swoosh recomputes everything each run, so inserting
the missing `ad_attributions` row retroactively fixes prior runs, and the
dashboard's recency window ages the stale error out on its own.

### Tests

- `swoosh/ad_attributions_test.go` — the pure three-way-split and extraction
  tests, plus DB-backed `swooshStudy` tests (needs `make test-db`).
- The ad-attribution section of `sources/fly/main_test.go`.

See `documentation/ad-attributions.md` and `planning/ad-id-attribution.md` for
more detail, including the write side in `adopt`.

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
