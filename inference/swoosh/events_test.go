package main

// Integration tests for the study_run_events writer (planning/study-errors-surfacing.md).
// Scope: swoosh is a WRITER. These tests assert only the facts swoosh writes
// (event types, fingerprints, severity, details). The derivation query that
// turns those facts into "current open errors" (DISTINCT ON + recency
// predicate) is owned by the read side — the adopt API's /errors endpoint —
// and its semantics (run_ok supersession, recency age-out, first_seen) are
// tested there, not here.

import (
	"context"
	"encoding/json"
	"testing"

	"github.com/jackc/pgx/v4/pgxpool"
	"github.com/stretchr/testify/assert"
	. "github.com/vlab-research/vlab/inference/test-helpers"
)

func countEvents(t *testing.T, pool *pgxpool.Pool, study, eventType string) int {
	var n int
	err := pool.QueryRow(context.Background(),
		`SELECT count(*) FROM study_run_events WHERE study_id = $1 AND event_type = $2`,
		study, eventType).Scan(&n)
	assert.Nil(t, err)
	return n
}

// An unmapped source must produce: run_started, one extraction_warning with the
// per-source fingerprint and aggregated details, and run_ok (the run itself is
// healthy — unmapped sources are skipped, not fatal).
func TestSwooshStudy_EmitsExtractionWarningAndRunOKForUnmappedSource(t *testing.T) {
	pool := TestPool()
	defer pool.Close()

	resetDb(pool)

	study := CreateStudy(pool, "studyA")
	activeDate := `{"start_date": "2020-01-10T00:00:00", "end_date": "2999-01-31T00:00:00"}`
	MustExec(t, pool, insertConf, study, "recruitment", activeDate)
	MustExec(t, pool, insertConf, study, "inference_data", infConfA)
	insertEvent(t, pool, study, "sIcNrF05", "foo_raw", `{"value": "true"}`)
	insertEvent(t, pool, study, "sIcNrF05", "foo_raw", `{"value": "true"}`)

	err := swooshStudy(pool, study)
	assert.Nil(t, err)

	assert.Equal(t, 1, countEvents(t, pool, study, "run_started"))
	assert.Equal(t, 1, countEvents(t, pool, study, "extraction_warning"))
	assert.Equal(t, 1, countEvents(t, pool, study, "run_ok"))

	var fingerprint, severity, message, runID string
	var details []byte
	err = pool.QueryRow(context.Background(),
		`SELECT fingerprint, severity, message, run_id, details
		 FROM study_run_events
		 WHERE study_id = $1 AND event_type = 'extraction_warning'`,
		study).Scan(&fingerprint, &severity, &message, &runID, &details)
	assert.Nil(t, err)

	assert.Equal(t, "inference:extraction:source=sIcNrF05", fingerprint)
	assert.Equal(t, "warning", severity)
	assert.Contains(t, message, "sIcNrF05")
	assert.NotEqual(t, "", runID, "facts of one run must share a run_id")

	var d map[string]interface{}
	assert.Nil(t, json.Unmarshal(details, &d))
	assert.Equal(t, "sIcNrF05", d["source"])
	assert.Equal(t, float64(2), d["count"], "two skipped events aggregate into one warning with count=2")
	assert.Contains(t, d["sources_in_mapping"], "fly")
}

// A healthy study emits run_started + run_ok only — no problem facts.
func TestSwooshStudy_EmitsOnlyRunFactsForHealthyStudy(t *testing.T) {
	pool := TestPool()
	defer pool.Close()

	resetDb(pool)

	study := CreateStudy(pool, "studyB")
	activeDate := `{"start_date": "2020-01-10T00:00:00", "end_date": "2999-01-31T00:00:00"}`
	MustExec(t, pool, insertConf, study, "recruitment", activeDate)
	MustExec(t, pool, insertConf, study, "inference_data", infConfA)
	insertEvent(t, pool, study, "fly", "foo_raw", `{"value": "true"}`)

	err := swooshStudy(pool, study)
	assert.Nil(t, err)

	assert.Equal(t, 1, countEvents(t, pool, study, "run_started"))
	assert.Equal(t, 1, countEvents(t, pool, study, "run_ok"))

	var problemFacts int
	err = pool.QueryRow(context.Background(),
		`SELECT count(*) FROM study_run_events WHERE study_id = $1 AND severity != ''`,
		study).Scan(&problemFacts)
	assert.Nil(t, err)
	assert.Equal(t, 0, problemFacts)
}

// run_ok and run_error share the inference:run fingerprint — this is the
// writer-side contract that lets the read side close an open error when a
// later run succeeds. A skip (no inference_data conf) is a healthy outcome and
// must also emit run_ok.
func TestSwooshStudy_SkipEmitsRunOKOnSharedFingerprint(t *testing.T) {
	pool := TestPool()
	defer pool.Close()

	resetDb(pool)

	study := CreateStudy(pool, "studyC")
	activeDate := `{"start_date": "2020-01-10T00:00:00", "end_date": "2999-01-31T00:00:00"}`
	MustExec(t, pool, insertConf, study, "recruitment", activeDate)
	// No inference_data conf → swooshStudy skips.

	err := swooshStudy(pool, study)
	assert.Nil(t, err)

	var fingerprint, severity string
	err = pool.QueryRow(context.Background(),
		`SELECT fingerprint, severity FROM study_run_events
		 WHERE study_id = $1 AND event_type = 'run_ok'`,
		study).Scan(&fingerprint, &severity)
	assert.Nil(t, err)
	assert.Equal(t, "inference:run", fingerprint)
	assert.Equal(t, "", severity)
}

// Event writes are best-effort: a study id that violates the FK must not break
// the run — RecordEvent logs and swallows.
func TestRecordEvent_IsBestEffort(t *testing.T) {
	pool := TestPool()
	defer pool.Close()

	resetDb(pool)

	// Not a real study id — the FK rejects the insert; RecordEvent must not panic.
	RecordEvent(pool, "00000000-0000-0000-0000-000000000000",
		"inference", "run-x", "run_ok", "inference:run", "", "", nil)

	assert.Equal(t, 0, countEvents(t, pool, "00000000-0000-0000-0000-000000000000", "run_ok"))
}
