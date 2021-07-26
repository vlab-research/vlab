package main

import (
	"encoding/json"
	"testing"

	"github.com/stretchr/testify/assert"
)

const (
	inferenceDataSql = `
                drop table if exists inference_data;

                create table if not exists inference_data(
		    study VARCHAR NOT NULL,
		    user_id VARCHAR NOT NULL,
                    variable VARCHAR NOT NULL,
                    data JSONB NOT NULL,
		    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
		    CONSTRAINT study_user UNIQUE(study, user_id, variable)
                );
`
)

func str(s string) *string {
	return &s
}

func TestInferenceDataWriterWritesMultipleTimesAndUpdatesDataRemovingVariables(t *testing.T) {
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

	e := WriteInferenceData(pool, "foo", id)
	handle(e)

	users := getCol(pool, "inference_data", "user_id")
	assert.Equal(t, 5, len(users))

	d := InferenceDataValue{ti("07"), "q1", []byte(`"A"`), "categorical"}

	id = InferenceData{"foo": {"foo", map[string]*InferenceDataValue{"q1": &d}}}
	e = WriteInferenceData(pool, "foo", id)
	handle(e)

	dat := getCol(pool, "inference_data", "data")
	dv := new(InferenceDataValue)
	json.Unmarshal([]byte(*dat[0]), dv)

	users = getCol(pool, "inference_data", "user_id")
	assert.Equal(t, []*string{str("foo")}, users)

	assert.Equal(t, 1, len(dat))
	assert.Equal(t, d, *dv)

}
