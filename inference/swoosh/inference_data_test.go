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
		"foo": {"foo",
			map[string]*InferenceDataValue{
				"name": {ti("07"), "name", []byte(`1`), "continuous"},
			}},
	}

	val := &InferenceDataValue{ti("07"), "name", []byte(`1`), "continuous"}
	iid := IntermediateInferenceData{"source": id}
	res, err := addValue(conf, iid, "foo", "source", val)

	assert.Nil(t, err)
	assert.Equal(t, expected, res["source"])

	val = &InferenceDataValue{ti("08"), "name", []byte(`0`), "continuous"}
	res, err = addValue(conf, iid, "foo", "source", val)

	assert.Nil(t, err)
	assert.Equal(t, expected, res["source"])

	val = &InferenceDataValue{ti("09"), "name", []byte(`2`), "continuous"}
	res, err = addValue(conf, iid, "foo", "source", val)

	expected = InferenceData{
		"foo": {"foo",
			map[string]*InferenceDataValue{
				"name": {ti("09"), "name", []byte(`2`), "continuous"},
			}},
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
		"foo": {"foo",
			map[string]*InferenceDataValue{
				"name": {ti("07"), "name", []byte(`1`), "continuous"},
			}},
	}

	val := &InferenceDataValue{ti("07"), "name", []byte(`1`), "continuous"}
	res, err := addValue(conf, iid, "foo", "source", val)

	assert.Nil(t, err)
	assert.Equal(t, expected, res["source"])

	expected = InferenceData{
		"foo": {"foo",
			map[string]*InferenceDataValue{
				"name": {ti("08"), "name", []byte(`0`), "continuous"},
			}},
	}
	val = &InferenceDataValue{ti("08"), "name", []byte(`0`), "continuous"}
	res, err = addValue(conf, iid, "foo", "source", val)

	assert.Nil(t, err)
	assert.Equal(t, expected, res["source"])
}

func TestReduceInferenceData_SelectsVariablesAsPerConfAndSelectFunction(t *testing.T) {
	events := testEvents("events_c.json")

	expected := InferenceData{
		"foo": {"foo",
			map[string]*InferenceDataValue{
				"renamed_q1": {ti("07"), "renamed_q1", []byte(`"yes"`), "categorical"},
			}},
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
		"foo": {"foo",
			map[string]*InferenceDataValue{
				"q1":                   {ti("07"), "q1", []byte(`"A"`), "categorical"},
				"q2":                   {ti("07"), "q2", []byte(`"B"`), "categorical"},
				"custom_user_variable": {ti("07"), "custom_user_variable", []byte(`"foo"`), "categorical"},
			}},
		"bar": {"bar",
			map[string]*InferenceDataValue{
				"q1": {ti("07"), "q1", []byte(`"C"`), "categorical"},
			}},
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
		"foo": {"foo",
			map[string]*InferenceDataValue{
				"first_event": {ti("07"), "first_event", []byte(`"A"`), "categorical"},
			}},
		"bar": {"bar",
			map[string]*InferenceDataValue{
				"first_event": {ti("10"), "first_event", []byte(`"A"`), "categorical"},
			}},
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
		"foo": {"foo",
			map[string]*InferenceDataValue{
				"other_md": {ti("07"), "other_md", []byte(`"value"`), "categorical"},
			}},
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
		"foo": {"foo",
			map[string]*InferenceDataValue{
				"other_md": {ti("07"), "other_md", []byte(`"value"`), "categorical"},
			}},
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
							Params:   []byte(`{"path": "", "key": "key"}`),
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
		"foo": {"foo",
			map[string]*InferenceDataValue{
				"other_md": {ti("07"), "other_md", []byte(`"value"`), "categorical"},
			}},
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
		"foo": {"foo",
			map[string]*InferenceDataValue{
				"q1": {ti("07"), "q1", []byte(`5`), "continuous"},
			}},
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
			"foo": {"foo",
				map[string]*InferenceDataValue{
					"q1": {ti("07"), "q1", []byte(`1`), "continuous"},
					"q2": {ti("07"), "q2", []byte(`2`), "continuous"},
				}},
		},
		"source2": InferenceData{
			"foo2": {"foo2",
				map[string]*InferenceDataValue{
					"q3":                   {ti("07"), "q3", []byte(`3`), "continuous"},
					"q4":                   {ti("07"), "q4", []byte(`4`), "continuous"},
					"custom_user_variable": {ti("07"), "custom_user_variable", []byte(`"foo"`), "categorical"},
				}},
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
			"foo": {"foo",
				map[string]*InferenceDataValue{
					"q1": {ti("07"), "q1", []byte(`1`), "continuous"},
					"q2": {ti("07"), "q2", []byte(`2`), "continuous"},
				}},
		},
		"source2": InferenceData{
			"foo": {"foo",
				map[string]*InferenceDataValue{
					"q3": {ti("07"), "q3", []byte(`3`), "continuous"},
					"q4": {ti("07"), "q4", []byte(`4`), "continuous"},
				}},
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
			"foo": {"foo",
				map[string]*InferenceDataValue{
					"q1": {ti("07"), "q1", []byte(`1`), "continuous"},
					"q2": {ti("07"), "q2", []byte(`2`), "continuous"},
				}},
		},
		"source2": InferenceData{
			"foo2": {"foo2",
				map[string]*InferenceDataValue{
					"q3": {ti("07"), "q3", []byte(`3`), "continuous"},
					"q4": {ti("07"), "q4", []byte(`4`), "continuous"},
				}},
		},
	}

	res, errors := JoinSources(intermediateData, confs)
	assert.Equal(t, 1, len(errors))
	assert.Equal(t, 2, len(res["foo"].Data))
	assert.Equal(t, "2", string(res["foo"].Data["q2"].Value))
	assert.Equal(t, "1", string(res["foo"].Data["q1"].Value))
}
