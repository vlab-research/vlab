package main

import (
	"context"
	"fmt"
	"testing"

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
	tableNames := []string{"inference_data_events", "study_confs", "studies", "users"}
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

	events, err := GetEvents(pool, foo)

	expected := []*InferenceDataEvent([]*InferenceDataEvent{})

	assert.Nil(t, err)
	assert.Equal(t, expected, events)
}
