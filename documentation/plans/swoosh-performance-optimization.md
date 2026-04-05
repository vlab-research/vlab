# Swoosh Performance Optimization Plan

## Overview

Swoosh is a Go-based ETL pipeline that extracts, transforms, and aggregates event data from multiple sources (Fly, Qualtrics, Typeform, Alchemer) into inference data for research studies.

**Current Pain Point**: The pipeline runs too slowly, particularly for studies with large event volumes.

---

## Critical Bottlenecks Identified

### 1. Full Table DELETE Before Insert (CRITICAL)

**Location**: `persist.go:29-30`

```go
// TODO: this is very expensive and silly, should be optimized
_, err = tx.Exec(context.Background(), "DELETE FROM inference_data WHERE study_id = $1", study)
```

**Problem**: Every write cycle deletes ALL historical inference_data for a study before inserting new rows. For large datasets, this causes O(n) deletion overhead on every run.

**Impact**: As inference_data grows, deletion time becomes prohibitive.

---

### 2. Row-by-Row INSERT in Nested Loops (CRITICAL)

**Location**: `persist.go:36-43`

```go
for user, row := range id {
    for variable, row := range row.Data {
        err = InsertInferenceData(tx, study, user, variable, ...)
    }
}
```

**Problem**: Individual INSERT statements for each user-variable combination. For N users with M variables each, this results in N×M database round trips.

**Impact**: Studies with 10,000 users and 50 variables = 500,000 individual INSERT queries per write cycle.

---

### 3. Regex Compiled on Every Call (CRITICAL)

**Location**: `extraction_functions.go:103`

```go
func (p *RegexpExtractParams) GetValue(dat json.RawMessage) ([]byte, error) {
    m, err := regexp.Compile(p.Regexp)  // Compiling regex on EVERY call
    ...
}
```

**Problem**: The same regex pattern is compiled repeatedly for every event processed. Regex compilation is expensive.

**Impact**: For millions of events, this adds significant CPU overhead.

---

### 4. Unbounded Event Query (HIGH)

**Location**: `swoosh.go:64`

```go
rows, err := pool.Query(context.Background(), query, study)
// ... then appends ALL results to a slice
```

**Problem**: Loads ALL events for a study into memory at once with no pagination.

**Impact**: Memory exhaustion for studies with large event volumes. No streaming/batching.

---

### 5. Sequential Study Processing (HIGH)

**Location**: `swoosh.go:112-136`

```go
for _, study := range studies {
    events, _ := GetEvents(pool, study)
    conf, _ := GetInferenceDataConf(pool, study)
    // ... process and write
}
```

**Problem**: Studies are processed one at a time with no parallelism.

**Impact**: Total runtime scales linearly with number of studies, even though studies are independent.

---

### 6. No Timeouts on Database Operations (HIGH)

**Location**: All database calls

**Problem**: All operations use `context.Background()` which never times out.

**Impact**: Hung queries block indefinitely with no recovery mechanism.

---

## Optimization Recommendations

### Priority 1: Fix DELETE + INSERT Pattern

**Current approach** (expensive):
1. DELETE all rows for study
2. INSERT all rows one by one

**Why DELETE is needed**: The DELETE cannot simply be removed because some data may no longer be valid on subsequent runs. For example, if a user's data is removed from source events or extraction configuration changes, that data should not persist in inference_data. The current approach ensures a clean slate but is expensive.

**Recommended approach**: Replace bulk DELETE with targeted reconciliation

Option A: **Delete-by-absence pattern**
1. Batch INSERT/UPSERT all current data
2. DELETE rows that weren't touched in this run (using a "last_updated" timestamp or run_id)

```sql
-- Add run_id or updated_at column to track freshness
-- After batch insert:
DELETE FROM inference_data
WHERE study_id = $1 AND updated_at < $2  -- Delete stale rows only
```

Option B: **Compute diff and delete explicitly**
1. Query existing (user, variable) pairs for the study
2. Compare with new data to find rows that should be removed
3. DELETE only the specific rows that are no longer valid
4. UPSERT the rest

Option C: **Soft delete with cleanup**
1. Mark all rows for study as "pending_delete"
2. UPSERT new data (clears the pending flag)
3. DELETE rows still marked "pending_delete"

**Trade-offs**:
- Option A requires schema change but is cleanest
- Option B adds query overhead but no schema change
- Option C is safest for debugging but adds complexity

---

### Priority 2: Batch INSERT Operations

**Current**: N×M individual INSERT statements

**Recommended**: Use "manyify" pattern (see `adopt/adopt/db.py:40-49`)

The manyify pattern builds a single INSERT with multiple value tuples:

```python
# Python reference from adopt/adopt/db.py
def manyify(q, vals):
    placeholders = "(" + ", ".join(["%s" for _ in cols]) + ")"
    placeholders = ", ".join([placeholders for _ in vals])
    vals = [y for x in vals for y in x]
    q = q + " values " + placeholders
    return q, vals
```

**Go implementation approach**:

```go
func batchInsert(tx pgx.Tx, study string, data InferenceData) error {
    const batchSize = 1000

    var values []interface{}
    var placeholders []string
    paramIdx := 1

    for user, row := range data {
        for variable, val := range row.Data {
            placeholders = append(placeholders,
                fmt.Sprintf("($%d, $%d, $%d, $%d, $%d, $%d)",
                    paramIdx, paramIdx+1, paramIdx+2, paramIdx+3, paramIdx+4, paramIdx+5))
            values = append(values, study, user, variable, val.Type, val.Value, val.Timestamp)
            paramIdx += 6

            if len(placeholders) >= batchSize {
                // Execute batch
                query := "INSERT INTO inference_data (...) VALUES " +
                    strings.Join(placeholders, ", ") + " ON CONFLICT ..."
                tx.Exec(ctx, query, values...)
                // Reset
                values = nil
                placeholders = nil
                paramIdx = 1
            }
        }
    }
    // Execute remaining
    ...
}
```

**Note**: CockroachDB (current version) doesn't support COPY, but batch INSERT with multiple VALUES works well. COPY will be available after CockroachDB upgrade.

---

### Priority 3: Cache Compiled Regexes

**Current**:
```go
func (p *RegexpExtractParams) GetValue(dat json.RawMessage) ([]byte, error) {
    m, err := regexp.Compile(p.Regexp)  // Every call!
    ...
}
```

**Recommended**:
```go
type RegexpExtractParams struct {
    Regexp   string
    compiled *regexp.Regexp  // Cached compiled regex
}

func (p *RegexpExtractParams) GetValue(dat json.RawMessage) ([]byte, error) {
    if p.compiled == nil {
        var err error
        p.compiled, err = regexp.Compile(p.Regexp)
        if err != nil {
            return nil, err
        }
    }
    // Use p.compiled instead of compiling fresh
    ...
}
```

---

### Priority 4: Add Parallel Study Processing

**Current**: Sequential for loop

**Recommended**: Worker pool with goroutines

```go
func processStudies(pool *pgxpool.Pool, studies []string, workers int) {
    jobs := make(chan string, len(studies))
    results := make(chan error, len(studies))

    // Start workers
    for w := 0; w < workers; w++ {
        go func() {
            for study := range jobs {
                err := processStudy(pool, study)
                results <- err
            }
        }()
    }

    // Send jobs
    for _, study := range studies {
        jobs <- study
    }
    close(jobs)

    // Collect results
    for range studies {
        if err := <-results; err != nil {
            log.Printf("Error: %v", err)
        }
    }
}
```

**Consideration**: Configure worker count based on database connection pool size.

---

### Priority 5: Paginate/Stream Events

**Current**: Load all events into memory

**Recommended**: Process in batches

```go
func GetEventsBatched(pool *pgxpool.Pool, study string, batchSize int, callback func([]Event) error) error {
    offset := 0
    for {
        query := `SELECT * FROM inference_data_events
                  WHERE study_id = $1
                  ORDER BY timestamp
                  LIMIT $2 OFFSET $3`

        rows, err := pool.Query(ctx, query, study, batchSize, offset)
        // ... scan into batch

        if len(batch) == 0 {
            break
        }

        if err := callback(batch); err != nil {
            return err
        }

        offset += batchSize
    }
    return nil
}
```

---

### Priority 6: Add Context Timeouts

**Current**: `context.Background()` everywhere

**Recommended**:
```go
ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
defer cancel()

rows, err := pool.Query(ctx, query, study)
```

---

## Implementation Order

1. **Cache compiled regexes** - Quick win, low risk, high impact
2. **Batch INSERT operations** - High impact, moderate complexity
3. **Replace bulk DELETE with targeted reconciliation** - High impact, requires schema change or additional queries
4. **Add context timeouts** - Quick win, improves reliability
5. **Parallel study processing** - High impact, moderate complexity
6. **Paginate events** - Prevents memory issues at scale

---

## Metrics to Track

Before and after optimization, measure:

- Total runtime for full pipeline
- Time per study
- Database query count
- Memory usage (peak)
- Events processed per second

---

## Notes

- Database is CockroachDB (older version), not PostgreSQL
- COPY not available until CockroachDB upgrade
- Batch INSERT with multiple VALUES tuples is the recommended approach
- See `adopt/adopt/db.py:manyify` for reference implementation pattern
