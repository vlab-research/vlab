package main

import (
	"bytes"
	"encoding/json"
	"fmt"

	"github.com/go-playground/validator/v10"

	. "github.com/vlab-research/vlab/inference/inference-data"
)

// TODO: validate not empty fields...?
type ExtractionConf struct {
	Key       string          `json:"key"`
	Name      string          `json:"name"`
	Function  string          `json:"function"`
	Params    json.RawMessage `json:"params"`
	ValueType string          `json:"value_type"`
	Aggregate string          `json:"aggregate"` // first, last, max, min
	fn        func(json.RawMessage) ([]byte, error)
}

type InferenceDataSource struct {
	VariableExtractionMapping []*ExtractionConf `json:"variable_extraction"`
	MetadataExtractionMapping []*ExtractionConf `json:"metadata_extraction"`
}

type InferenceDataConf struct {
	DataSources map[string]*InferenceDataSource `json:"data_sources"`
}

func (c InferenceDataConf) Sources() []string {
	m := c.DataSources
	i := 0
	keys := make([]string, len(m))
	for k := range m {
		keys[i] = k
		i++
	}
	return keys
}

func (conf *ExtractionConf) Extract(dat json.RawMessage) ([]byte, error) {
	if conf.fn == nil {

		var p ExtractionFunctionParams
		switch conf.Function {

		case "select":
			p = new(SelectFunctionParams)

		case "vlab-kv-pair-select":
			p = new(VlabKVPairSelectFunctionParams)

		}

		err := json.Unmarshal(conf.Params, p)
		if err != nil {
			return nil, fmt.Errorf(
				"Could not parse function params for function %s. Param json: %s. Parsing error: %s.",
				conf.Function,
				string(conf.Params),
				err)
		}

		v := validator.New()
		err = v.Struct(p)
		if err != nil {
			return nil, err
		}

		conf.fn = p.GetValue

	}

	raw, err := conf.fn(dat)
	if err != nil {
		return nil, err
	}

	return CastValue(conf, raw)
}

// TODO: this casting is pretty silly...
// We were happily transparently flowing raw json through as value
// until all the sudden we needed to compare...
func getNumericValues(oldVal, val *InferenceDataValue) (float64, float64, error) {
	o, err := CastContinuous(oldVal.Value)
	if err != nil {
		return 0, 0, err
	}
	n, err := CastContinuous(val.Value)
	if err != nil {
		return o, 0, err
	}
	return o, n, nil
}

func addValue(conf *ExtractionConf, id InferenceData, user string, val *InferenceDataValue) (InferenceData, error) {
	_, ok := id[user]

	if !ok {
		id[user] = &InferenceDataRow{user, make(map[string]*InferenceDataValue)}
	}

	oldVal, ok := id[user].Data[val.Variable]

	if !ok {
		id[user].Data[val.Variable] = val
		return id, nil
	}

	if bytes.Equal(oldVal.Value, val.Value) {
		return id, nil
	}

	switch conf.Aggregate {
	case "last":
		if oldVal.Timestamp.Before(val.Timestamp) {
			id[user].Data[val.Variable] = val
		}
		return id, nil

	case "first":
		if oldVal.Timestamp.After(val.Timestamp) {
			id[user].Data[val.Variable] = val
		}
		return id, nil

	case "max":
		// TODO: this casting is pretty silly...
		o, n, err := getNumericValues(oldVal, val)
		if err != nil {
			return id, err
		}

		if o < n {
			id[user].Data[val.Variable] = val
		}
		return id, nil

	case "min":
		o, n, err := getNumericValues(oldVal, val)
		if err != nil {
			return id, err
		}

		if o > n {
			id[user].Data[val.Variable] = val
		}
		return id, nil

	default:
		return id, fmt.Errorf("Could not find match for aggregate function: %s", conf.Aggregate)
	}
}

func retrieveFromMetadata(e *InferenceDataEvent, conf *ExtractionConf) (json.RawMessage, bool) {
	v, ok := e.User.Metadata[conf.Key]
	return v, ok
}

func retrieveFromVariable(e *InferenceDataEvent, conf *ExtractionConf) (json.RawMessage, bool) {
	ok := e.Variable == conf.Key
	return e.Value, ok
}

func extractValue(id InferenceData, e *InferenceDataEvent, extractionConfs []*ExtractionConf, retrieve func(*InferenceDataEvent, *ExtractionConf) (json.RawMessage, bool)) (InferenceData, error) {
	for _, conf := range extractionConfs {

		val, ok := retrieve(e, conf)
		if !ok {
			continue
		}

		val, err := conf.Extract(val)
		if err != nil {
			return nil, err
		}

		v := &InferenceDataValue{e.Timestamp, conf.Name, val, conf.ValueType}

		id, err := addValue(conf, id, e.User.ID, v)
		if err != nil {
			return id, err
		}
	}

	return id, nil
}

func Reduce(events []*InferenceDataEvent, c *InferenceDataConf) (InferenceData, error) {
	id := make(InferenceData)

	for _, e := range events {

		sourceConf, ok := c.DataSources[e.SourceConf.Name]

		if !ok {
			return nil, fmt.Errorf("Attempted to process event from data source not in SourceVariableMapping. "+
				"Data source: %s. Sources in mapping: %s",
				e.SourceConf.Name,
				c.Sources())
		}

		// attempt to extract the values from the user metadata, according to config
		// TODO: should this have a nil check? Preferably not!

		// add from metadata
		id, err := extractValue(id, e, sourceConf.MetadataExtractionMapping, retrieveFromMetadata)

		if err != nil {
			return id, err
		}

		// attempt to extract the values from the event itself, according to config
		id, err = extractValue(id, e, sourceConf.VariableExtractionMapping, retrieveFromVariable)
		if err != nil {
			bb, _ := json.Marshal(e)
			fmt.Println("Error extracting value: " + string(bb))
			return id, err
		}
	}

	return id, nil
}
