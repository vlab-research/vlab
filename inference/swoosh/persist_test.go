package main

import (
	"context"
	"encoding/json"
	"fmt"
	"testing"

	"github.com/stretchr/testify/assert"
	. "github.com/vlab-research/vlab/inference/inference-data"
	. "github.com/vlab-research/vlab/inference/test-helpers"
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
	pool := TestPool()
	defer pool.Close()
	MustExec(t, pool, inferenceDataSql)

	id := InferenceData{
		"foo": {
			User: "foo",
			Data: map[string]*InferenceDataValue{
				"user_md": {Timestamp: ti("09"), Variable: "user_md", Value: []byte(`"foo"`), ValueType: "metadata"},
				"q1":      {Timestamp: ti("07"), Variable: "q1", Value: []byte(`"A"`), ValueType: "categorical"},
				"q2":      {Timestamp: ti("09"), Variable: "q2", Value: []byte(`2`), ValueType: "continuous"},
			},
		},
		"bar": {
			User: "bar",
			Data: map[string]*InferenceDataValue{
				"user_md": {Timestamp: ti("10"), Variable: "user_md", Value: []byte(`"bar"`), ValueType: "metadata"},
				"q2":      {Timestamp: ti("10"), Variable: "q2", Value: []byte(`2`), ValueType: "continuous"},
			},
		},
	}

	e := WriteInferenceData(pool, "study_foo", id)
	handle(e)

	// Writes 5 lines to database, one for each variable/value
	users := GetCol(pool, "inference_data", "user_id")
	assert.Equal(t, 5, len(users))

	// Now, overwrites all data from study_foo with a single variable/user
	id = InferenceData{
		"foo": {
			User: "foo",
			Data: map[string]*InferenceDataValue{
				"q1": {Timestamp: ti("07"), Variable: "q1", Value: []byte(`"A"`), ValueType: "categorical"},
			},
		},
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
	users = GetCol(pool, "inference_data", "user_id")
	assert.Equal(t, []*string{str("foo")}, users)
	assert.Equal(t, 1, len(users))

}

func TestBatchInsertInferenceData_ExactlyBatchSize(t *testing.T) {
	pool := TestPool()
	defer pool.Close()
	MustExec(t, pool, inferenceDataSql)

	// Create exactly 500 rows (batch size)
	id := InferenceData{}
	for i := 0; i < 500; i++ {
		userId := fmt.Sprintf("user%d", i)
		id[userId] = &InferenceDataRow{
			User: userId,
			Data: map[string]*InferenceDataValue{
				"q1": {Timestamp: ti("10"), Variable: "q1", Value: []byte(`"A"`), ValueType: "categorical"},
			},
		}
	}

	e := WriteInferenceData(pool, "study_batch_test", id)
	assert.Nil(t, e)

	// Verify all 500 rows were inserted
	users := GetCol(pool, "inference_data", "user_id")
	assert.Equal(t, 500, len(users))
}

func TestBatchInsertInferenceData_MoreThanBatchSize(t *testing.T) {
	pool := TestPool()
	defer pool.Close()
	MustExec(t, pool, inferenceDataSql)

	// Create 501 rows (batch size + 1) to test mid-iteration flush
	id := InferenceData{}
	for i := 0; i < 501; i++ {
		userId := fmt.Sprintf("user%d", i)
		id[userId] = &InferenceDataRow{
			User: userId,
			Data: map[string]*InferenceDataValue{
				"q1": {Timestamp: ti("10"), Variable: "q1", Value: []byte(`"B"`), ValueType: "categorical"},
			},
		}
	}

	e := WriteInferenceData(pool, "study_batch_test", id)
	assert.Nil(t, e)

	// Verify all 501 rows were inserted (500 in first batch, 1 in final flush)
	users := GetCol(pool, "inference_data", "user_id")
	assert.Equal(t, 501, len(users))
}

func TestBatchInsertInferenceData_LessThanBatchSize(t *testing.T) {
	pool := TestPool()
	defer pool.Close()
	MustExec(t, pool, inferenceDataSql)

	// Create 50 rows (less than batch size)
	id := InferenceData{}
	for i := 0; i < 50; i++ {
		userId := fmt.Sprintf("user%d", i)
		id[userId] = &InferenceDataRow{
			User: userId,
			Data: map[string]*InferenceDataValue{
				"q1": {Timestamp: ti("10"), Variable: "q1", Value: []byte(`"C"`), ValueType: "categorical"},
			},
		}
	}

	e := WriteInferenceData(pool, "study_batch_test", id)
	assert.Nil(t, e)

	// Verify all 50 rows were inserted
	users := GetCol(pool, "inference_data", "user_id")
	assert.Equal(t, 50, len(users))
}

func TestBatchInsertInferenceData_EmptyData(t *testing.T) {
	pool := TestPool()
	defer pool.Close()
	MustExec(t, pool, inferenceDataSql)

	// Test with empty InferenceData
	id := InferenceData{}

	e := WriteInferenceData(pool, "study_batch_test", id)
	assert.Nil(t, e)

	// Verify no rows were inserted
	users := GetCol(pool, "inference_data", "user_id")
	assert.Equal(t, 0, len(users))
}

func TestBatchInsertInferenceData_MultipleVariablesPerUser(t *testing.T) {
	pool := TestPool()
	defer pool.Close()
	MustExec(t, pool, inferenceDataSql)

	// Create data with multiple variables per user to test batching logic
	id := InferenceData{}
	// 250 users * 3 variables = 750 total rows (will trigger batch flush)
	for i := 0; i < 250; i++ {
		userId := fmt.Sprintf("user%d", i)
		id[userId] = &InferenceDataRow{
			User: userId,
			Data: map[string]*InferenceDataValue{
				"q1": {Timestamp: ti("10"), Variable: "q1", Value: []byte(`"A"`), ValueType: "categorical"},
				"q2": {Timestamp: ti("10"), Variable: "q2", Value: []byte(`2`), ValueType: "continuous"},
				"q3": {Timestamp: ti("10"), Variable: "q3", Value: []byte(`"D"`), ValueType: "categorical"},
			},
		}
	}

	e := WriteInferenceData(pool, "study_batch_test", id)
	assert.Nil(t, e)

	// Verify all rows were inserted (250 users * 3 variables = 750 rows)
	rows, err := pool.Query(context.Background(), "select user_id, variable from inference_data order by user_id, variable")
	assert.Nil(t, err)

	count := 0
	for rows.Next() {
		count++
	}
	assert.Equal(t, 750, count)
}

func TestBatchInsertInferenceData_UpsertBehavior(t *testing.T) {
	pool := TestPool()
	defer pool.Close()
	MustExec(t, pool, inferenceDataSql)

	// First insert
	id1 := InferenceData{
		"user1": {
			User: "user1",
			Data: map[string]*InferenceDataValue{
				"q1": {Timestamp: ti("10"), Variable: "q1", Value: []byte(`"initial"`), ValueType: "categorical"},
			},
		},
	}

	e := WriteInferenceData(pool, "study_upsert_test", id1)
	assert.Nil(t, e)

	// Second insert with same user/variable, different value
	id2 := InferenceData{
		"user1": {
			User: "user1",
			Data: map[string]*InferenceDataValue{
				"q1": {Timestamp: ti("11"), Variable: "q1", Value: []byte(`"updated"`), ValueType: "categorical"},
			},
		},
	}

	e = WriteInferenceData(pool, "study_upsert_test", id2)
	assert.Nil(t, e)

	// Verify value was updated (not duplicated)
	rows, err := pool.Query(context.Background(), "select value from inference_data where study_id = 'study_upsert_test'")
	assert.Nil(t, err)

	values := []json.RawMessage{}
	for rows.Next() {
		var msg json.RawMessage
		err = rows.Scan(&msg)
		assert.Nil(t, err)
		values = append(values, msg)
	}

	assert.Equal(t, 1, len(values))
	assert.Equal(t, json.RawMessage([]byte(`"updated"`)), values[0])
}

// TODO: Add tests for error handling and consider the handling well
