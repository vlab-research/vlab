package main

import (
	"context"
	"encoding/json"
	"fmt"
	"testing"
	"time"

	"github.com/jackc/pgx/v4/pgxpool"
	"github.com/stretchr/testify/assert"
	. "github.com/vlab-research/vlab/inference/inference-data"
	. "github.com/vlab-research/vlab/inference/test-helpers"
)

const (
	infConfA = `
        {
           "data_sources": {
               "fly": {
                   "extraction_confs": [{
                          "location": "variable",
                          "key": "foo_raw",
			  "name": "foo",
                          "functions": [{"function": "select", "params": { "path": "value" }}],
			  "value_type": "existence"
                      }]
                }
           }
        }
       `

	infConfB = `
        {
           "data_sources": {
               "fly": {
                   "extraction_confs": [{
                          "location": "variable",
                          "key": "foo_raw",
			  "name": "bar",
                          "functions": [{"function": "select", "params": { "path": "value" }}],
			  "value_type": "existence"
                      }]
             }
          }
        }
       `

	insertUser = `insert into users(id) values($1) returning id`
	insertConf = `insert into study_confs(study_id, conf_type, conf) values($1, $2, $3)`
)

func resetDb(pool *pgxpool.Pool) {
	tableNames := []string{"study_run_events", "inference_data", "inference_data_events", "study_confs", "studies", "users"}
	query := ""
	for _, table := range tableNames {
		query += fmt.Sprintf("DELETE FROM %s; ", table)
	}

	_, err := pool.Exec(context.Background(), query)
	if err != nil {
		panic(err)
	}
}

func TestGetInferenceDataConf_GetsLatestConf(t *testing.T) {
	pool := TestPool()
	defer pool.Close()

	resetDb(pool)

	foo := CreateStudy(pool, "foo")

	MustExec(t, pool, insertConf, foo, "inference_data", infConfB)
	MustExec(t, pool, insertConf, foo, "inference_data", infConfA)

	expected := &InferenceDataConf{map[string]*DataSource{
		"fly": {
			ExtractionConfs: []*ExtractionConf{
				{
					Location:  "variable",
					Key:       "foo_raw",
					Name:      "foo",
					ValueType: "existence",
					Functions: []ExtractionFunctionConf{
						{
							Function: "select",
							Params:   []byte(`{"path": "value"}`),
						},
					},
				},
			},
		},
	}}

	actual, err := GetInferenceDataConf(pool, foo)
	assert.Nil(t, err)
	assert.Equal(t, expected, actual)
}

func TestGetEvents_WorksWithNoEvents(t *testing.T) {
	pool := TestPool()
	defer pool.Close()

	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	MustExec(t, pool, insertConf, foo, "inference_data", infConfA)

	events, err := GetEvents(pool, foo, []string{"fly"})

	expected := []*InferenceDataEvent([]*InferenceDataEvent{})

	assert.Nil(t, err)
	assert.Equal(t, expected, events)
}

const insertEventSQL = `INSERT INTO inference_data_events(study_id, source_name, timestamp, data, idx, pagination) VALUES($1, $2, $3, $4, $5, $6)`

func insertEvent(t *testing.T, pool *pgxpool.Pool, study, sourceName, variable, value string) {
	e := &InferenceDataEvent{
		User:       User{ID: "test-user"},
		Study:      study,
		SourceConf: &SourceConf{Name: sourceName},
		Timestamp:  time.Now().UTC(),
		Variable:   variable,
		Value:      json.RawMessage(value),
	}
	b, err := json.Marshal(e)
	if err != nil {
		t.Fatal(err)
	}
	MustExec(t, pool, insertEventSQL, study, sourceName, e.Timestamp, b, 0, "")
}

// TestSwooshStudy_IsolatesFailures proves that events from unmapped sources
// (e.g. mid-study source renames) are skipped gracefully without preventing
// other studies from being processed and stored. Study A has only unmapped
// sources (all events skipped); Study B has mapped sources (data written).
// Both succeed without blocking each other.
func TestSwooshStudy_IsolatesFailures(t *testing.T) {
	pool := TestPool()
	defer pool.Close()

	resetDb(pool)

	studyA := CreateStudy(pool, "studyA")
	studyB := CreateStudy(pool, "studyB")

	activeDate := `{"start_date": "2020-01-10T00:00:00", "end_date": "2999-01-31T00:00:00"}`
	MustExec(t, pool, insertConf, studyA, "recruitment", activeDate)
	MustExec(t, pool, insertConf, studyB, "recruitment", activeDate)

	// Study A: inference_data mapping keyed "fly", but event tagged "sIcNrF05"
	// (reproduces the production sIcNrF05/Fly mismatch crash from mid-study source rename).
	// With the fix, unmapped sources are skipped gracefully (not fatal).
	MustExec(t, pool, insertConf, studyA, "inference_data", infConfA)
	insertEvent(t, pool, studyA, "sIcNrF05", "foo_raw", `{"value": "true"}`)

	// Study B: healthy — event source "fly" matches the mapping key.
	MustExec(t, pool, insertConf, studyB, "inference_data", infConfA)
	insertEvent(t, pool, studyB, "fly", "foo_raw", `{"value": "true"}`)

	// Study A should succeed (unmapped sources are skipped, not fatal).
	errA := swooshStudy(pool, studyA)
	assert.Nil(t, errA, "Study A should succeed (unmapped sources are skipped, not fatal)")

	// Study B should also succeed.
	errB := swooshStudy(pool, studyB)
	assert.Nil(t, errB, "Study B should succeed")

	// Study B's inference_data rows must have landed.
	var countB int
	err := pool.QueryRow(context.Background(),
		`SELECT COUNT(*) FROM inference_data WHERE study_id = $1`, studyB).Scan(&countB)
	assert.Nil(t, err)
	assert.Equal(t, 1, countB, "Study B should have inference data written")

	// Study A should have no inference_data (all events skipped, no rows written).
	var countA int
	err = pool.QueryRow(context.Background(),
		`SELECT COUNT(*) FROM inference_data WHERE study_id = $1`, studyA).Scan(&countA)
	assert.Nil(t, err)
	assert.Equal(t, 0, countA, "Study A should have no inference data (all events from unmapped source skipped)")
}
