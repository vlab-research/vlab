package main

import (
	"context"
	"fmt"
	"testing"

	"github.com/jackc/pgx/v4/pgxpool"
	"github.com/stretchr/testify/assert"
	. "github.com/vlab-research/vlab/inference/test-helpers"
)

const (
	infConfA = `
        {
           "data_sources": {
               "fly": {
                  "variable_extraction": [
                      {
                          "key": "foo_raw",
			  "name": "foo",
			  "function": "select",
			  "params": { "path": "value" },
			  "value_type": "existence"
                      }
                  ],
                  "metadata_extraction": []
              }
           }
        }
       `

	infConfB = `
        {
           "data_sources": {
               "fly": {
                  "variable_extraction": [
                      {
                          "key": "foo_raw",
			  "name": "bar",
			  "function": "select",
			  "params": { "path": "value" },
			  "value_type": "existence"
                      }
                  ],
                  "metadata_extraction": []
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

	expected := &InferenceDataConf{map[string]*InferenceDataSource{
		"fly": {
			VariableExtractionMapping: []*ExtractionConf{
				{Key: "foo_raw", Name: "foo", ValueType: "existence", Function: "select", Params: []byte(`{"path": "value"}`)},
			},
			MetadataExtractionMapping: []*ExtractionConf{},
		},
	}}

	actual, err := GetInferenceDataConf(pool, foo)
	assert.Nil(t, err)
	assert.Equal(t, expected, actual)
}
