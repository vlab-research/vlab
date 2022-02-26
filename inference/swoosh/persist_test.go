package main

import (
	"context"
	"encoding/json"
	"testing"

	"github.com/stretchr/testify/assert"
	. "github.com/vlab-research/vlab/inference/inference-data"
)

const (
	inferenceDataSql = `
                drop table if exists inference_data;

                create table if not exists inference_data(
		    study_id VARCHAR NOT NULL,
		    user_id VARCHAR NOT NULL,
                    variable VARCHAR NOT NULL,
                    value_type VARCHAR NOT NULL,
                    value JSONB NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL,
		    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
		    CONSTRAINT study_user UNIQUE(study_id, user_id, variable)
                );
`
)

func str(s string) *string {
	return &s
}

func TestInferenceDataWriter_WritesMultipleTimesAndUpdatesDataRemovingVariables(t *testing.T) {
	pool := testPool()
	defer pool.Close()
	mustExec(t, pool, inferenceDataSql)

	id := InferenceData{
		"foo": {"foo",
			map[string]*InferenceDataValue{
				"user_md": {ti("09"), "user_md", []byte(`"foo"`), "metadata"},
				"q1":      {ti("07"), "q1", []byte(`"A"`), "categorical"},
				"q2":      {ti("09"), "q2", []byte(`2`), "continuous"},
			}},
		"bar": {"bar",
			map[string]*InferenceDataValue{
				"user_md": {ti("10"), "user_md", []byte(`"bar"`), "metadata"},
				"q2":      {ti("10"), "q2", []byte(`2`), "continuous"},
			}},
	}

	e := WriteInferenceData(pool, "study_foo", id)
	handle(e)

	// Writes 5 lines to database, one for each variable/value
	users := getCol(pool, "inference_data", "user_id")
	assert.Equal(t, 5, len(users))

	// Now, overwrites all data from study_foo with a single variable/user
	id = InferenceData{
		"foo": {"foo",
			map[string]*InferenceDataValue{
				"q1": {ti("07"), "q1", []byte(`"A"`), "categorical"},
			}},
	}
	e = WriteInferenceData(pool, "study_foo", id)
	handle(e)

	// Assert all data is overwritten.
	// custom parsing logic to asser that it's a json rawmessage of the same
	// data we started with.
	rows, err := pool.Query(context.Background(), "select value from inference_data")
	handle(err)
	res := []json.RawMessage{}
	for rows.Next() {
		var msg json.RawMessage
		err = rows.Scan(&msg)
		handle(err)
		res = append(res, msg)

	}

	assert.Equal(t, 1, len(res))
	assert.Equal(t, json.RawMessage([]byte(`"A"`)), res[0])

	// Assert only one user now, foo
	users = getCol(pool, "inference_data", "user_id")
	assert.Equal(t, []*string{str("foo")}, users)
	assert.Equal(t, 1, len(users))

}

// TODO: Add tests for error handling and consider the handling well
