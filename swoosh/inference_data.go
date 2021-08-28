package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"time"

	"github.com/go-playground/validator/v10"
)

type User struct {
	ID       string                     `json:"id"`
	Metadata map[string]json.RawMessage `json:"metadata"`
}

type InferenceDataEvent struct {
	User       User            `json:"user"`
	Study      string          `json:"study"`
	DataSource string          `json:"data_source"`
	Timestamp  time.Time       `json:"timestamp"`
	Variable   string          `json:"variable"`
	Value      json.RawMessage `json:"value"`
}

type InferenceDataValue struct {
	Timestamp time.Time       `json:"timestamp"`
	Variable  string          `json:"variable"`
	Value     json.RawMessage `json:"value"`
	ValueType string          `json:"value_type"`
}

type InferenceDataRow struct {
	User string                         `json:"user"`
	Data map[string]*InferenceDataValue `json:"data"`
}

type InferenceData map[string]*InferenceDataRow

// TODO: validate not empty fields...?
type ExtractionConf struct {
	Name     string          `json:"name"`
	Function string          `json:"function"`
	Params   json.RawMessage `json:"params"`
	Type     string          `json:"type"`
	fn       func(json.RawMessage) ([]byte, error)
}

type InferenceDataSource struct {
	VariableExtractionMapping map[string]*ExtractionConf // source variable name -> extraction conf
	MetadataExtractionMapping map[string]*ExtractionConf // source variable name -> extraction conf
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

	return conf.fn(dat)
}

func addValue(id InferenceData, user string, val *InferenceDataValue) InferenceData {
	_, ok := id[user]

	if !ok {
		id[user] = &InferenceDataRow{user, make(map[string]*InferenceDataValue)}
	}

	oldVal, ok := id[user].Data[val.Variable]

	if ok {
		if bytes.Equal(oldVal.Value, val.Value) {
			return id
		}
	}

	id[user].Data[val.Variable] = val
	return id
}

func extractValue(e *InferenceDataEvent, extractionConfs map[string]*ExtractionConf) (*InferenceDataValue, error) {
	// Now deal with the main value from the event
	conf, ok := extractionConfs[e.Variable]
	if !ok {
		return nil, nil
	}

	val, err := conf.Extract(e.Value)
	if err != nil {
		return nil, err
	}

	return &InferenceDataValue{e.Timestamp, conf.Name, val, conf.Type}, nil
}

func extractMetadata(e *InferenceDataEvent, extractionConfs map[string]*ExtractionConf) []*InferenceDataValue {
	vals := []*InferenceDataValue{}

	// Every event might have user metadata of interest, so we need to look at all of it
	for k, conf := range extractionConfs {
		v, ok := e.User.Metadata[k]
		if !ok {
			continue
		}

		vals = append(vals, &InferenceDataValue{e.Timestamp, conf.Name, v, conf.Type})
	}

	return vals
}

func Reduce(events []*InferenceDataEvent, c *InferenceDataConf) (InferenceData, error) {
	id := make(InferenceData)

	for _, e := range events {
		sourceConf, ok := c.DataSources[e.DataSource]

		if !ok {
			return nil, fmt.Errorf("Attempted to process event from data source not in SourceVariableMapping. "+
				"Data source: %s. Sources in mapping: %s",
				e.DataSource,
				c.Sources())
		}

		// attempt to extract the values from the user metadata, according to config
		vals := extractMetadata(e, sourceConf.MetadataExtractionMapping)

		// attempt to extract the values from the event itself, according to config
		val, err := extractValue(e, sourceConf.VariableExtractionMapping)
		if err != nil {
			return id, err
		}
		if val != nil {
			vals = append(vals, val)
		}

		// add the variable to the InferenceData
		for _, v := range vals {
			addValue(id, e.User.ID, v)
		}
	}

	return id, nil
}
