package main

import (
	"encoding/json"
	"fmt"
	"github.com/stretchr/testify/assert"
	"io/ioutil"
	"testing"
	"time"
)

func testEvents(fi string) []*InferenceDataEvent {
	b, e := ioutil.ReadFile(fmt.Sprintf("test/%s", fi))
	check(e)

	events := []InferenceDataEvent{}
	e = json.Unmarshal(b, &events)
	check(e)

	res := []*InferenceDataEvent{}

	for i := range events {
		res = append(res, &events[i])
	}

	return res
}

func check(e error) {
	if e != nil {
		panic(e)
	}
}

func ti(day string) time.Time {
	t, e := time.Parse("2006-01-02", fmt.Sprintf("2021-07-%s", day))
	check(e)
	return t.UTC()
}

func TestAddValue_PicksMax(t *testing.T) {
	conf := &ExtractionConf{
		Name:      "name",
		Type:      "categorical",
		Function:  "select",
		Params:    []byte(`{"path": "translated_response"}`),
		Aggregate: "max",
	}

	id := make(InferenceData)

	expected := InferenceData{
		"foo": {"foo",
			map[string]*InferenceDataValue{
				"name": {ti("07"), "name", []byte(`1`), "continuous"},
			}},
	}

	val := &InferenceDataValue{ti("07"), "name", []byte(`1`), "continuous"}
	actual, err := addValue(conf, id, "foo", val)

	assert.Nil(t, err)
	assert.Equal(t, expected, actual)

	val = &InferenceDataValue{ti("08"), "name", []byte(`0`), "continuous"}
	actual, err = addValue(conf, id, "foo", val)

	assert.Nil(t, err)
	assert.Equal(t, expected, actual)

	val = &InferenceDataValue{ti("09"), "name", []byte(`2`), "continuous"}
	actual, err = addValue(conf, id, "foo", val)

	expected = InferenceData{
		"foo": {"foo",
			map[string]*InferenceDataValue{
				"name": {ti("09"), "name", []byte(`2`), "continuous"},
			}},
	}

	assert.Nil(t, err)
	assert.Equal(t, expected, actual)
}

func TestAddValue_PicksLast(t *testing.T) {
	conf := &ExtractionConf{
		Name:      "name",
		Type:      "categorical",
		Function:  "select",
		Params:    []byte(`{"path": "translated_response"}`),
		Aggregate: "last",
	}

	id := make(InferenceData)

	expected := InferenceData{
		"foo": {"foo",
			map[string]*InferenceDataValue{
				"name": {ti("07"), "name", []byte(`1`), "continuous"},
			}},
	}

	val := &InferenceDataValue{ti("07"), "name", []byte(`1`), "continuous"}
	actual, err := addValue(conf, id, "foo", val)

	assert.Nil(t, err)
	assert.Equal(t, expected, actual)

	expected = InferenceData{
		"foo": {"foo",
			map[string]*InferenceDataValue{
				"name": {ti("08"), "name", []byte(`0`), "continuous"},
			}},
	}
	val = &InferenceDataValue{ti("08"), "name", []byte(`0`), "continuous"}
	actual, err = addValue(conf, id, "foo", val)

	assert.Nil(t, err)
	assert.Equal(t, expected, actual)
}

func TestReduceInferenceData_SelectsVariablesAsPerConfAndSelectFunction(t *testing.T) {
	events := testEvents("events_c.json")

	expected := InferenceData{
		"foo": {"foo",
			map[string]*InferenceDataValue{
				"renamed_q1": {ti("07"), "renamed_q1", []byte(`"yes"`), "categorical"},
			}},
	}

	mapping := &InferenceDataConf{map[string]*InferenceDataSource{
		"literacy_data_api": {
			map[string]*ExtractionConf{
				"q1": {
					Name:     "renamed_q1",
					Type:     "categorical",
					Function: "select",
					Params:   []byte(`{"path": "translated_response"}`),
				}},
			nil,
		},
	}}

	actual, err := Reduce(events, mapping)
	assert.Nil(t, err)
	assert.Equal(t, expected, actual)
}

func TestReduceInferenceData_GroupsByUserAndOverwritesRepeatedValues(t *testing.T) {
	events := testEvents("events_a.json")

	expected := InferenceData{
		"foo": {"foo",
			map[string]*InferenceDataValue{
				"q1": {ti("07"), "q1", []byte(`"A"`), "categorical"},
				"q2": {ti("09"), "q2", []byte(`2`), "continuous"}, // second value
			}},
		"bar": {"bar",
			map[string]*InferenceDataValue{
				"q2": {ti("10"), "q2", []byte(`2`), "continuous"},
			}},
	}

	mapping := &InferenceDataConf{map[string]*InferenceDataSource{
		"literacy_data_api": {
			VariableExtractionMapping: map[string]*ExtractionConf{
				"q1": {
					Name:      "q1",
					Type:      "categorical",
					Function:  "select",
					Params:    []byte(`{"path": ""}`),
					Aggregate: "last",
				},
				"q2": {
					Name:      "q2",
					Type:      "continuous",
					Function:  "select",
					Params:    []byte(`{"path": ""}`),
					Aggregate: "last",
				},
			},
			MetadataExtractionMapping: nil,
		},
	}}

	actual, err := Reduce(events, mapping)
	assert.Nil(t, err)
	assert.Equal(t, expected, actual)
}

func TestReduceInferenceData_CollectsMetadataWithTimestampFirstEventOfUniqueValue(t *testing.T) {
	events := testEvents("events_b.json")

	expected := InferenceData{
		"foo": {"foo",
			map[string]*InferenceDataValue{
				"some_md": {ti("07"), "some_md", []byte(`"foo"`), "categorical"}, // time of first event
				"q1":      {ti("07"), "q1", []byte(`"A"`), "categorical"},
				"q2":      {ti("08"), "q2", []byte(`0`), "continuous"},
			}},
		"bar": {"bar",
			map[string]*InferenceDataValue{
				"some_md": {ti("11"), "some_md", []byte(`"baz"`), "categorical"}, // time of second event
				"q1":      {ti("10"), "q1", []byte(`"A"`), "categorical"},
				"q2":      {ti("11"), "q2", []byte(`2`), "continuous"},
			}},
	}

	mapping := &InferenceDataConf{map[string]*InferenceDataSource{
		"literacy_data_api": {
			VariableExtractionMapping: map[string]*ExtractionConf{
				"q1": {
					Name:      "q1",
					Type:      "categorical",
					Function:  "select",
					Params:    []byte(`{"path": ""}`),
					Aggregate: "last",
				},
				"q2": {
					Name:      "q2",
					Type:      "continuous",
					Function:  "select",
					Params:    []byte(`{"path": ""}`),
					Aggregate: "last",
				},
			},
			MetadataExtractionMapping: map[string]*ExtractionConf{
				"user_md": {
					Name:      "some_md",
					Type:      "categorical",
					Function:  "select",
					Params:    []byte(`{"path": ""}`),
					Aggregate: "last",
				},
			},
		},
	}}

	actual, err := Reduce(events, mapping)
	assert.Nil(t, err)
	assert.Equal(t, expected, actual)
}

func TestReduceInferenceData_ReturnsErrorWhenNonExistantDataSource(t *testing.T) {
	events := testEvents("events_a.json")

	mapping := &InferenceDataConf{map[string]*InferenceDataSource{
		"foo": {
			VariableExtractionMapping: map[string]*ExtractionConf{
				"bar": {},
			},
			MetadataExtractionMapping: nil,
		},
		"bar": {
			VariableExtractionMapping: map[string]*ExtractionConf{
				"baz": {},
			},
			MetadataExtractionMapping: nil,
		},
	}}

	_, err := Reduce(events, mapping)
	assert.NotNil(t, err)
	assert.Contains(t, err.Error(), "literacy_data_api")
	assert.Contains(t, err.Error(), "foo")
	assert.Contains(t, err.Error(), "bar")
}

func TestReduceInferenceData_ReturnsErrorWhenInvalidExtractionParamsForFunction(t *testing.T) {
	events := testEvents("events_a.json")

	mapping := &InferenceDataConf{map[string]*InferenceDataSource{
		"literacy_data_api": {
			VariableExtractionMapping: map[string]*ExtractionConf{
				"q1": {Function: "select", Params: []byte(`{"missing": "key"}`)},
			},
			MetadataExtractionMapping: nil,
		},
	}}

	_, err := Reduce(events, mapping)
	assert.NotNil(t, err)
	assert.Contains(t, err.Error(), "Path")

	mapping = &InferenceDataConf{map[string]*InferenceDataSource{
		"literacy_data_api": {
			VariableExtractionMapping: map[string]*ExtractionConf{
				"q1": {Function: "select", Params: []byte(`notjson`)},
			},
			MetadataExtractionMapping: nil,
		},
	}}

	_, err = Reduce(events, mapping)
	assert.NotNil(t, err)
	assert.Contains(t, err.Error(), "select")
	assert.Contains(t, err.Error(), "notjson")
}

func TestReduceInferenceData_ReturnsErrorWhenExtractionFunctionFails(t *testing.T) {
	events := testEvents("events_a.json")

	mapping := &InferenceDataConf{map[string]*InferenceDataSource{
		"literacy_data_api": {
			VariableExtractionMapping: map[string]*ExtractionConf{
				"q1": {Function: "select", Params: []byte(`{"path": "does.not.exist.in.json"}`)},
			},
			MetadataExtractionMapping: nil,
		},
	}}

	_, err := Reduce(events, mapping)
	assert.NotNil(t, err)
	assert.Contains(t, err.Error(), "does.not.exist.in.json")
	assert.Contains(t, err.Error(), "\"A\"")
}
