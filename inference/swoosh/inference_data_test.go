package main

import (
	"encoding/json"
	"fmt"
	"github.com/stretchr/testify/assert"
	. "github.com/vlab-research/vlab/inference/inference-data"
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
		Location:  "variable",
		Key:       "key",
		Name:      "name",
		ValueType: "categorical",
		Functions: []ExtractionFunctionConf{
			{
				Function: "select",
				Params:   []byte(`{"path": "translated_response"}`),
			},
		},
		Aggregate: "max",
	}

	id := make(InferenceData)

	expected := InferenceData{
		"foo": {
			User: "foo",
			Data: map[string]*InferenceDataValue{
				"name": {Timestamp: ti("07"), Variable: "name", Value: []byte(`1`), ValueType: "continuous"},
			},
		},
	}

	val := &InferenceDataValue{Timestamp: ti("07"), Variable: "name", Value: []byte(`1`), ValueType: "continuous"}
	iid := IntermediateInferenceData{"source": id}
	res, err := addValue(conf, iid, "foo", "source", val)

	assert.Nil(t, err)
	assert.Equal(t, expected, res["source"])

	val = &InferenceDataValue{Timestamp: ti("08"), Variable: "name", Value: []byte(`0`), ValueType: "continuous"}
	res, err = addValue(conf, iid, "foo", "source", val)

	assert.Nil(t, err)
	assert.Equal(t, expected, res["source"])

	val = &InferenceDataValue{Timestamp: ti("09"), Variable: "name", Value: []byte(`2`), ValueType: "continuous"}
	res, err = addValue(conf, iid, "foo", "source", val)

	expected = InferenceData{
		"foo": {
			User: "foo",
			Data: map[string]*InferenceDataValue{
				"name": {Timestamp: ti("09"), Variable: "name", Value: []byte(`2`), ValueType: "continuous"},
			},
		},
	}

	assert.Nil(t, err)
	assert.Equal(t, expected, res["source"])
}

func TestAddValue_PicksLast(t *testing.T) {
	conf := &ExtractionConf{
		Key:       "name",
		Name:      "name",
		ValueType: "categorical",
		Functions: []ExtractionFunctionConf{
			{
				Function: "select",
				Params:   []byte(`{"path": "translated_response"}`),
			},
		},
		Aggregate: "last",
	}

	id := make(InferenceData)
	iid := IntermediateInferenceData{"source": id}

	expected := InferenceData{
		"foo": {
			User: "foo",
			Data: map[string]*InferenceDataValue{
				"name": {Timestamp: ti("07"), Variable: "name", Value: []byte(`1`), ValueType: "continuous"},
			},
		},
	}

	val := &InferenceDataValue{Timestamp: ti("07"), Variable: "name", Value: []byte(`1`), ValueType: "continuous"}
	res, err := addValue(conf, iid, "foo", "source", val)

	assert.Nil(t, err)
	assert.Equal(t, expected, res["source"])

	expected = InferenceData{
		"foo": {
			User: "foo",
			Data: map[string]*InferenceDataValue{
				"name": {Timestamp: ti("08"), Variable: "name", Value: []byte(`0`), ValueType: "continuous"},
			},
		},
	}
	val = &InferenceDataValue{Timestamp: ti("08"), Variable: "name", Value: []byte(`0`), ValueType: "continuous"}
	res, err = addValue(conf, iid, "foo", "source", val)

	assert.Nil(t, err)
	assert.Equal(t, expected, res["source"])
}

func TestReduceInferenceData_SelectsVariablesAsPerConfAndSelectFunction(t *testing.T) {
	events := testEvents("events_c.json")

	expected := InferenceData{
		"foo": {
			User: "foo",
			Data: map[string]*InferenceDataValue{
				"renamed_q1": {Timestamp: ti("07"), Variable: "renamed_q1", Value: []byte(`"yes"`), ValueType: "categorical"},
			},
		},
	}

	mapping := &InferenceDataConf{map[string]*DataSource{
		"lit_data": {
			ExtractionConfs: []*ExtractionConf{
				{
					Location:  "variable",
					Key:       "q1",
					Name:      "renamed_q1",
					ValueType: "categorical",
					Functions: []ExtractionFunctionConf{
						{
							Function: "select",
							Params:   []byte(`{"path": "translated_response"}`),
						},
					},
				},
			},
		},
	}}

	actual, extractionErrors, err := Reduce(events, mapping)
	assert.Nil(t, err)
	assert.Equal(t, len(extractionErrors), 0)
	assert.Equal(t, expected, actual)
}

func TestReduceInferenceData_GroupsByUserAndOverwritesRepeatedValues(t *testing.T) {
	events := testEvents("events_a.json")

	expected := InferenceData{
		"foo": {
			User: "foo",
			Data: map[string]*InferenceDataValue{
				"q1": {Timestamp: ti("07"), Variable: "q1", Value: []byte(`"A"`), ValueType: "categorical"},
				"q2": {Timestamp: ti("09"), Variable: "q2", Value: []byte(`2`), ValueType: "continuous"}, // second value
			},
		},
		"bar": {
			User: "bar",
			Data: map[string]*InferenceDataValue{
				"q2": {Timestamp: ti("10"), Variable: "q2", Value: []byte(`2`), ValueType: "continuous"},
			},
		},
	}

	mapping := &InferenceDataConf{map[string]*DataSource{
		"lit_data": {
			ExtractionConfs: []*ExtractionConf{
				{
					Location:  "variable",
					Key:       "q1",
					Name:      "q1",
					ValueType: "categorical",
					Functions: []ExtractionFunctionConf{
						{
							Function: "select",
							Params:   []byte(`{"path": ""}`),
						},
					},
					Aggregate: "last",
				},
				{
					Location:  "variable",
					Key:       "q2",
					Name:      "q2",
					ValueType: "continuous",
					Functions: []ExtractionFunctionConf{
						{
							Function: "select",
							Params:   []byte(`{"path": ""}`),
						},
					},
					Aggregate: "last",
				},
			},
		},
	}}

	actual, extractionErrors, err := Reduce(events, mapping)
	assert.Nil(t, err)
	assert.Equal(t, len(extractionErrors), 0)
	assert.Equal(t, expected, actual)
}

func TestReduceInferenceData_GroupsByUserFromMultipleSourcesIncludingUserVariable(t *testing.T) {
	events := testEvents("events_g.json")

	expected := InferenceData{
		"foo": {
			User: "foo",
			Data: map[string]*InferenceDataValue{
				"q1":                   {Timestamp: ti("07"), Variable: "q1", Value: []byte(`"A"`), ValueType: "categorical"},
				"q2":                   {Timestamp: ti("07"), Variable: "q2", Value: []byte(`"B"`), ValueType: "categorical"},
				"custom_user_variable": {Timestamp: ti("07"), Variable: "custom_user_variable", Value: []byte(`"foo"`), ValueType: "categorical"},
			},
		},
		"bar": {
			User: "bar",
			Data: map[string]*InferenceDataValue{
				"q1": {Timestamp: ti("07"), Variable: "q1", Value: []byte(`"C"`), ValueType: "categorical"},
			},
		},
	}

	mapping := &InferenceDataConf{map[string]*DataSource{
		"source1": {
			ExtractionConfs: []*ExtractionConf{
				{
					Location:  "variable",
					Key:       "q1",
					Name:      "q1",
					ValueType: "categorical",
					Functions: []ExtractionFunctionConf{
						{
							Function: "select",
							Params:   []byte(`{"path": ""}`),
						},
					},
					Aggregate: "last",
				},
			},
		},
		"source2": {
			UserVariable: "custom_user_variable",
			ExtractionConfs: []*ExtractionConf{
				{
					Location:  "variable",
					Key:       "q1",
					Name:      "q1",
					ValueType: "categorical",
					Functions: []ExtractionFunctionConf{
						{
							Function: "select",
							Params:   []byte(`{"path": ""}`),
						},
					},
					Aggregate: "last",
				},
				{
					Location:  "variable",
					Key:       "q2",
					Name:      "q2",
					ValueType: "categorical",
					Functions: []ExtractionFunctionConf{
						{
							Function: "select",
							Params:   []byte(`{"path": ""}`),
						},
					},
					Aggregate: "last",
				},
				{
					Location:  "variable",
					Key:       "custom_user_variable",
					Name:      "custom_user_variable",
					ValueType: "categorical",
					Functions: []ExtractionFunctionConf{
						{
							Function: "select",
							Params:   []byte(`{"path": ""}`),
						},
					},
					Aggregate: "last",
				},
			},
		},
	}}

	actual, extractionErrors, err := Reduce(events, mapping)
	assert.Nil(t, err)
	assert.Equal(t, len(extractionErrors), 0)
	assert.Equal(t, expected, actual)
}

func TestReduceInferenceData_CollectsMetadataWithTimestampFirstEventOfUniqueValue(t *testing.T) {
	events := testEvents("events_b.json")

	expected := InferenceData{
		"foo": {
			User: "foo",
			Data: map[string]*InferenceDataValue{
				"some_md": {Timestamp: ti("07"), Variable: "some_md", Value: []byte(`"foo"`), ValueType: "categorical"}, // time of first event
				"q1":      {Timestamp: ti("07"), Variable: "q1", Value: []byte(`"A"`), ValueType: "categorical"},
				"q2":      {Timestamp: ti("08"), Variable: "q2", Value: []byte(`0`), ValueType: "continuous"},
			},
		},
		"bar": {
			User: "bar",
			Data: map[string]*InferenceDataValue{
				"some_md": {Timestamp: ti("11"), Variable: "some_md", Value: []byte(`"baz"`), ValueType: "categorical"}, // time of second event
				"q1":      {Timestamp: ti("10"), Variable: "q1", Value: []byte(`"A"`), ValueType: "categorical"},
				"q2":      {Timestamp: ti("11"), Variable: "q2", Value: []byte(`2`), ValueType: "continuous"},
			},
		},
	}

	mapping := &InferenceDataConf{map[string]*DataSource{
		"lit_data": {

			ExtractionConfs: []*ExtractionConf{
				{
					Location:  "variable",
					Key:       "q1",
					Name:      "q1",
					ValueType: "categorical",
					Functions: []ExtractionFunctionConf{
						{
							Function: "select",
							Params:   []byte(`{"path": ""}`),
						},
					},
					Aggregate: "last",
				},
				{
					Location:  "variable",
					Key:       "q2",
					Name:      "q2",
					ValueType: "continuous",
					Functions: []ExtractionFunctionConf{
						{
							Function: "select",
							Params:   []byte(`{"path": ""}`),
						},
					},
					Aggregate: "last",
				},
				{
					Location:  "metadata",
					Key:       "user_md",
					Name:      "some_md",
					ValueType: "categorical",
					Functions: []ExtractionFunctionConf{
						{
							Function: "select",
							Params:   []byte(`{"path": ""}`),
						},
					},
					Aggregate: "last",
				},
			},
		},
	}}

	actual, extractionErrors, err := Reduce(events, mapping)
	assert.Nil(t, err)
	assert.Equal(t, len(extractionErrors), 0)
	assert.Equal(t, expected, actual)
}

func TestReduceInferenceData_CanExtractFirstVariable(t *testing.T) {
	// has json as metadata
	events := testEvents("events_b.json")

	expected := InferenceData{
		"foo": {
			User: "foo",
			Data: map[string]*InferenceDataValue{
				"first_event": {Timestamp: ti("07"), Variable: "first_event", Value: []byte(`"A"`), ValueType: "categorical"},
			},
		},
		"bar": {
			User: "bar",
			Data: map[string]*InferenceDataValue{
				"first_event": {Timestamp: ti("10"), Variable: "first_event", Value: []byte(`"A"`), ValueType: "categorical"},
			},
		},
	}

	mapping := &InferenceDataConf{map[string]*DataSource{
		"lit_data": {
			ExtractionConfs: []*ExtractionConf{
				{
					Location:  "variable",
					Key:       "*",
					Name:      "first_event",
					ValueType: "categorical",
					Functions: []ExtractionFunctionConf{
						{
							Function: "select",
							Params:   []byte(`{"path": ""}`),
						},
					},
					Aggregate: "first",
				},
			},
		},
	}}

	actual, extractionErrors, err := Reduce(events, mapping)
	assert.Nil(t, err)
	assert.Equal(t, len(extractionErrors), 0)
	assert.Equal(t, expected, actual)
}

func TestReduceInferenceData_UsesExtractionMappingOfMetadata(t *testing.T) {
	// has json as metadata
	events := testEvents("events_d.json")

	expected := InferenceData{
		"foo": {
			User: "foo",
			Data: map[string]*InferenceDataValue{
				"other_md": {Timestamp: ti("07"), Variable: "other_md", Value: []byte(`"value"`), ValueType: "categorical"},
			},
		},
	}

	mapping := &InferenceDataConf{map[string]*DataSource{
		"lit_data": {
			ExtractionConfs: []*ExtractionConf{
				{
					Location:  "metadata",
					Key:       "other_md",
					Name:      "other_md",
					ValueType: "categorical",
					Functions: []ExtractionFunctionConf{
						{
							Function: "select",
							Params:   []byte(`{"path": "key"}`),
						},
					},
					Aggregate: "last",
				},
			},
		},
	}}

	actual, extractionErrors, err := Reduce(events, mapping)
	assert.Nil(t, err)
	assert.Equal(t, len(extractionErrors), 0)
	assert.Equal(t, expected, actual)
}

func TestReduceInferenceData_WorksWithSelectKVPairFunction(t *testing.T) {
	events := testEvents("events_e.json")

	expected := InferenceData{
		"foo": {
			User: "foo",
			Data: map[string]*InferenceDataValue{
				"other_md": {Timestamp: ti("07"), Variable: "other_md", Value: []byte(`"value"`), ValueType: "categorical"},
			},
		},
	}

	mapping := &InferenceDataConf{map[string]*DataSource{
		"lit_data": {
			ExtractionConfs: []*ExtractionConf{
				{
					Location:  "metadata",
					Key:       "other_md",
					Name:      "other_md",
					ValueType: "categorical",
					Functions: []ExtractionFunctionConf{
						{
							Function: "vlab-kv-pair-select",
							Params:   []byte(`{"key": "key"}`),
						},
					},
					Aggregate: "last",
				},
			},
		},
	}}

	actual, extractionErrors, err := Reduce(events, mapping)
	assert.Nil(t, err)
	assert.Equal(t, len(extractionErrors), 0)
	assert.Equal(t, expected, actual)
}

func TestReduceInferenceData_WorksWithSelectMultipleChainedFunctions(t *testing.T) {
	events := testEvents("events_f.json")

	expected := InferenceData{
		"foo": {
			User: "foo",
			Data: map[string]*InferenceDataValue{
				"other_md": {Timestamp: ti("07"), Variable: "other_md", Value: []byte(`"value"`), ValueType: "categorical"},
			},
		},
	}

	mapping := &InferenceDataConf{map[string]*DataSource{
		"lit_data": {
			ExtractionConfs: []*ExtractionConf{
				{
					Location:  "metadata",
					Key:       "other_md",
					Name:      "other_md",
					ValueType: "categorical",
					Functions: []ExtractionFunctionConf{
						{
							Function: "select",
							Params:   []byte(`{"path": "key"}`),
						},
						{
							Function: "regexp-extract",
							Params:   []byte(`{"regexp": "[^\\d]+"}`),
						},
					},
					Aggregate: "last",
				},
			},
		},
	}}

	actual, extractionErrors, err := Reduce(events, mapping)
	assert.Nil(t, err)
	assert.Equal(t, len(extractionErrors), 0)
	assert.Equal(t, expected, actual)
}

func TestReduceInferenceData_WorksCastingStringsToContinuousValues(t *testing.T) {
	events := testEvents("events_e.json")

	expected := InferenceData{
		"foo": {
			User: "foo",
			Data: map[string]*InferenceDataValue{
				"q1": {Timestamp: ti("07"), Variable: "q1", Value: []byte(`5`), ValueType: "continuous"},
			},
		},
	}

	mapping := &InferenceDataConf{map[string]*DataSource{
		"lit_data": {
			ExtractionConfs: []*ExtractionConf{
				{
					Location:  "variable",
					Key:       "q1",
					Name:      "q1",
					ValueType: "continuous",
					Functions: []ExtractionFunctionConf{
						{
							Function: "select",
							Params:   []byte(`{"path": ""}`),
						},
					},
					Aggregate: "max",
				},
			},
		},
	}}

	actual, extractionErrors, err := Reduce(events, mapping)
	assert.Nil(t, err)
	assert.Equal(t, len(extractionErrors), 0)
	assert.Equal(t, expected, actual)
}

func TestReduceInferenceData_ReturnsErrorWhenNonExistantDataSource(t *testing.T) {
	events := testEvents("events_a.json")

	mapping := &InferenceDataConf{map[string]*DataSource{
		"foo": {},
		"bar": {},
	}}

	_, extractionErrors, err := Reduce(events, mapping)
	assert.Equal(t, len(extractionErrors), 0)
	assert.NotNil(t, err)
	assert.Contains(t, err.Error(), "lit_data")
	assert.Contains(t, err.Error(), "foo")
	assert.Contains(t, err.Error(), "bar")
}

func TestReduceInferenceData_SkipsUsersWhenInvalidExtractionParamsForFunction(t *testing.T) {
	events := testEvents("events_a.json")

	mapping := &InferenceDataConf{map[string]*DataSource{
		"lit_data": {
			ExtractionConfs: []*ExtractionConf{
				{
					Location: "variable",
					Key:      "q1",
					Functions: []ExtractionFunctionConf{
						{
							Function: "select",
							Params:   []byte(`{"missing": "key"}`),
						},
					},
				},
			},
		},
	}}

	_, extractionErrors, err := Reduce(events, mapping)
	assert.Nil(t, err)
	e := extractionErrors[0]
	assert.Contains(t, e.Error(), "Path")

	mapping = &InferenceDataConf{map[string]*DataSource{
		"lit_data": {
			ExtractionConfs: []*ExtractionConf{
				{
					Location: "variable",
					Key:      "q1",
					Functions: []ExtractionFunctionConf{
						{
							Function: "select",
							Params:   []byte(`notjson`)},
					},
				},
			},
		},
	}}

	_, extractionErrors, err = Reduce(events, mapping)
	assert.Nil(t, err)
	e = extractionErrors[0]
	assert.Contains(t, e.Error(), "select")
	assert.Contains(t, e.Error(), "notjson")
}

func TestReduceInferenceData_ReturnsExtractionErrorsWhenExtractionFunctionFails(t *testing.T) {
	events := testEvents("events_a.json")

	mapping := &InferenceDataConf{map[string]*DataSource{
		"lit_data": {
			ExtractionConfs: []*ExtractionConf{
				{
					Location: "variable",
					Key:      "q1",
					Functions: []ExtractionFunctionConf{
						{
							Function: "select",
							Params:   []byte(`{"path": "does.not.exist.in.json"}`)},
					},
				},
			},
		},
	}}

	_, extractionErrors, err := Reduce(events, mapping)
	assert.Nil(t, err)
	e := extractionErrors[0]

	assert.Contains(t, e.Error(), "does.not.exist.in.json")
	assert.Contains(t, e.Error(), "\"A\"")
}

func TestReduceInferenceData_ReturnsErrorWhenExtractionFunctionDoesNotExist(t *testing.T) {
	events := testEvents("events_a.json")

	mapping := &InferenceDataConf{map[string]*DataSource{
		"lit_data": {
			ExtractionConfs: []*ExtractionConf{
				{
					Location: "variable",
					Key:      "q1",
					Functions: []ExtractionFunctionConf{
						{
							Function: "nopenotathing",
							Params:   []byte(`{"path": "does.not.exist.in.json"}`)},
					},
				},
			},
		},
	}}

	_, extractionErrors, err := Reduce(events, mapping)
	assert.Nil(t, err)
	e := extractionErrors[0]
	assert.Contains(t, e.Error(), "nopenotathing")
}

func TestJoinSources_JoinsAllVariablesFromSourcesWithCustomUserVariable(t *testing.T) {
	confs := map[string]*DataSource{
		"source1": {},
		"source2": {
			UserVariable: "custom_user_variable",
		},
	}

	intermediateData := IntermediateInferenceData{
		"source1": InferenceData{
			"foo": {
				User: "foo",
				Data: map[string]*InferenceDataValue{
					"q1": {Timestamp: ti("07"), Variable: "q1", Value: []byte(`1`), ValueType: "continuous"},
					"q2": {Timestamp: ti("07"), Variable: "q2", Value: []byte(`2`), ValueType: "continuous"},
				},
			},
		},
		"source2": InferenceData{
			"foo2": {
				User: "foo2",
				Data: map[string]*InferenceDataValue{
					"q3":                   {Timestamp: ti("07"), Variable: "q3", Value: []byte(`3`), ValueType: "continuous"},
					"q4":                   {Timestamp: ti("07"), Variable: "q4", Value: []byte(`4`), ValueType: "continuous"},
					"custom_user_variable": {Timestamp: ti("07"), Variable: "custom_user_variable", Value: []byte(`"foo"`), ValueType: "categorical"},
				},
			},
		},
	}

	res, errors := JoinSources(intermediateData, confs)
	assert.Equal(t, 0, len(errors))
	assert.Equal(t, "4", string(res["foo"].Data["q4"].Value))
	assert.Equal(t, "3", string(res["foo"].Data["q3"].Value))
	assert.Equal(t, "2", string(res["foo"].Data["q2"].Value))
	assert.Equal(t, "1", string(res["foo"].Data["q1"].Value))
	assert.Equal(t, `"foo"`, string(res["foo"].Data["custom_user_variable"].Value))
}

func TestJoinSources_JoinsAllVariablesFromSourcesWithoutCustomUserVariable(t *testing.T) {
	confs := map[string]*DataSource{
		"source1": {},
		"source2": {},
	}

	intermediateData := IntermediateInferenceData{
		"source1": InferenceData{
			"foo": {
				User: "foo",
				Data: map[string]*InferenceDataValue{
					"q1": {Timestamp: ti("07"), Variable: "q1", Value: []byte(`1`), ValueType: "continuous"},
					"q2": {Timestamp: ti("07"), Variable: "q2", Value: []byte(`2`), ValueType: "continuous"},
				},
			},
		},
		"source2": InferenceData{
			"foo": {
				User: "foo",
				Data: map[string]*InferenceDataValue{
					"q3": {Timestamp: ti("07"), Variable: "q3", Value: []byte(`3`), ValueType: "continuous"},
					"q4": {Timestamp: ti("07"), Variable: "q4", Value: []byte(`4`), ValueType: "continuous"},
				},
			},
		},
	}

	res, errors := JoinSources(intermediateData, confs)
	assert.Equal(t, 0, len(errors))
	assert.Equal(t, "4", string(res["foo"].Data["q4"].Value))
	assert.Equal(t, "3", string(res["foo"].Data["q3"].Value))
	assert.Equal(t, "2", string(res["foo"].Data["q2"].Value))
	assert.Equal(t, "1", string(res["foo"].Data["q1"].Value))
}

func TestJoinSources_ReturnsErrorWhenMissingUserVarForSomeone(t *testing.T) {
	confs := map[string]*DataSource{
		"source1": {},
		"source2": {
			UserVariable: "custom_user_variable",
		},
	}

	intermediateData := IntermediateInferenceData{
		"source1": InferenceData{
			"foo": {
				User: "foo",
				Data: map[string]*InferenceDataValue{
					"q1": {Timestamp: ti("07"), Variable: "q1", Value: []byte(`1`), ValueType: "continuous"},
					"q2": {Timestamp: ti("07"), Variable: "q2", Value: []byte(`2`), ValueType: "continuous"},
				},
			},
		},
		"source2": InferenceData{
			"foo2": {
				User: "foo2",
				Data: map[string]*InferenceDataValue{
					"q3": {Timestamp: ti("07"), Variable: "q3", Value: []byte(`3`), ValueType: "continuous"},
					"q4": {Timestamp: ti("07"), Variable: "q4", Value: []byte(`4`), ValueType: "continuous"},
				},
			},
		},
	}

	res, errors := JoinSources(intermediateData, confs)
	assert.Equal(t, 1, len(errors))
	assert.Equal(t, 2, len(res["foo"].Data))
	assert.Equal(t, "2", string(res["foo"].Data["q2"].Value))
	assert.Equal(t, "1", string(res["foo"].Data["q1"].Value))
}
