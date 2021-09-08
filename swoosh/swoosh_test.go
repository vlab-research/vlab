package main

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

const (
	infConfA = `
        {
           "data_sources": {
               "fly": {
                  "variable_extraction": {
                      "foo_raw": {
			  "name": "foo",
			  "function": "select",
			  "params": { "path": "value" },
			  "type": "existence"
                      }
                  },
                  "metadata_extraction": {}
              }
           }
        }
       `

	infConfB = `
        {
           "data_sources": {
               "fly": {
                  "variable_extraction": {
                      "foo_raw": {
			  "name": "bar",
			  "function": "select",
			  "params": { "path": "value" },
			  "type": "existence"
                      }
                  },
                  "metadata_extraction": {}
              }
           }
        }
       `
)

func TestGetInferenceDataConf_GetsLatestConf(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, studiesSql)
	mustExec(t, pool, studyConfsSql)

	foo := createStudy(pool, "foo", true)
	mustExec(t, pool, insertConf, foo, "inference_data", infConfB)
	mustExec(t, pool, insertConf, foo, "inference_data", infConfA)

	expected := &InferenceDataConf{map[string]*InferenceDataSource{
		"fly": {
			VariableExtractionMapping: map[string]*ExtractionConf{
				"foo_raw": {Name: "foo", Type: "existence", Function: "select", Params: []byte(`{"path": "value"}`)},
			},
			MetadataExtractionMapping: map[string]*ExtractionConf{},
		},
	}}

	actual, err := GetInferenceDataConf(pool, foo)
	assert.Nil(t, err)
	assert.Equal(t, expected, actual)
}
