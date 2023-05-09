package main

import (
	"bytes"
	"encoding/json"
	"fmt"

	"github.com/go-playground/validator/v10"

	. "github.com/vlab-research/vlab/inference/inference-data"
)

type ExtractionFunctionConf struct {
	Function string          `json:"function"`
	Params   json.RawMessage `json:"params"`
}

type ExtractionFunction func(json.RawMessage) ([]byte, error)

// TODO: validate not empty fields...?
type ExtractionConf struct {
	Location  string                   `json:"location"`
	Key       string                   `json:"key"`
	Name      string                   `json:"name"`
	Functions []ExtractionFunctionConf `json:"functions"`
	ValueType string                   `json:"value_type"`
	Aggregate string                   `json:"aggregate"` // first, last, max, min
	fns       []ExtractionFunction
}

type DataSource struct {
	ExtractionConfs []*ExtractionConf `json:"extraction_confs"`
	UserVariable    string            `json:"user_variable"`
}

type InferenceDataConf struct {
	DataSources map[string]*DataSource `json:"data_sources"`
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
	// Chainable extraction functions???
	fns := []ExtractionFunction{}

	if conf.fns == nil {
		// for each func in funcs
		for _, c := range conf.Functions {

			var p ExtractionFunctionParams
			switch c.Function {

			// Add regexp select

			case "select":
				p = new(SelectFunctionParams)

			case "vlab-kv-pair-select":
				p = new(VlabKVPairSelectFunctionParams)

			case "regexp-extract":
				p = new(RegexpExtractParams)

			default:
				return nil, fmt.Errorf("Could not find function: %s", c.Function)

			}

			err := json.Unmarshal(c.Params, p)
			if err != nil {
				return nil, fmt.Errorf(
					"Could not parse function params for function %s. Param json: %s. Parsing error: %s.",
					c.Function,
					string(c.Params),
					err)
			}

			v := validator.New()
			err = v.Struct(p)
			if err != nil {
				return nil, err
			}

			// append func to funcs
			fns = append(fns, p.GetValue)
		}

		conf.fns = fns
	}

	// go through slice and apply each func
	raw := []byte(dat)
	for _, f := range conf.fns {
		var err error
		raw, err = f(raw)
		if err != nil {
			return nil, err
		}
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

func addValue(conf *ExtractionConf, id IntermediateInferenceData, user string, source string, val *InferenceDataValue) (IntermediateInferenceData, error) {

	_, ok := id[source]
	if !ok {
		id[source] = make(InferenceData)
	}

	_, ok = id[source][user]
	if !ok {
		id[source][user] = &InferenceDataRow{user, make(map[string]*InferenceDataValue)}
	}

	oldVal, ok := id[source][user].Data[val.Variable]

	if !ok {
		id[source][user].Data[val.Variable] = val
		return id, nil
	}

	if bytes.Equal(oldVal.Value, val.Value) {
		return id, nil
	}

	switch conf.Aggregate {
	case "last":
		if oldVal.Timestamp.Before(val.Timestamp) {
			id[source][user].Data[val.Variable] = val
		}
		return id, nil

	case "first":
		if oldVal.Timestamp.After(val.Timestamp) {
			id[source][user].Data[val.Variable] = val
		}
		return id, nil

	case "max":
		// TODO: this casting is pretty silly...
		o, n, err := getNumericValues(oldVal, val)
		if err != nil {
			return id, err
		}

		if o < n {
			id[source][user].Data[val.Variable] = val
		}
		return id, nil

	case "min":
		o, n, err := getNumericValues(oldVal, val)
		if err != nil {
			return id, err
		}

		if o > n {
			id[source][user].Data[val.Variable] = val
		}
		return id, nil

	default:
		return id, fmt.Errorf("Could not find match for aggregate function: %s", conf.Aggregate)
	}
}

type RetrieveFunc func(*InferenceDataEvent, *ExtractionConf) (json.RawMessage, bool)

func retrieveFromMetadata(e *InferenceDataEvent, conf *ExtractionConf) (json.RawMessage, bool) {
	v, ok := e.User.Metadata[conf.Key]
	return v, ok
}

func retrieveFromVariable(e *InferenceDataEvent, conf *ExtractionConf) (json.RawMessage, bool) {
	if conf.Key == "*" {
		return e.Value, true
	}
	ok := e.Variable == conf.Key
	return e.Value, ok
}

func getRetrieveFunc(conf *ExtractionConf) (RetrieveFunc, error) {
	switch conf.Location {
	case "variable":
		return retrieveFromVariable, nil
	case "metadata":
		return retrieveFromMetadata, nil
	}

	return nil, fmt.Errorf("Could not find location function for location: %s", conf.Location)
}

func extractValue(id IntermediateInferenceData, e *InferenceDataEvent, extractionConfs []*ExtractionConf) (IntermediateInferenceData, error) {

	for _, conf := range extractionConfs {
		retrieve, err := getRetrieveFunc(conf)
		if err != nil {
			return id, err
		}

		val, ok := retrieve(e, conf)
		if !ok {
			continue
		}

		val, err = conf.Extract(val)
		if err != nil {
			return id, err
		}

		v := &InferenceDataValue{e.Timestamp, conf.Name, val, conf.ValueType}

		id, err = addValue(conf, id, e.User.ID, e.SourceConf.Name, v)
		if err != nil {
			return id, err
		}
	}

	return id, nil
}

func JoinSources(intermediateData IntermediateInferenceData, confs map[string]*DataSource) (InferenceData, []error) {

	errs := []error{}
	infData := make(InferenceData)

	for source, val := range intermediateData {

		conf := confs[source] // has to exist by now

		// map user names
		for user, row := range val {
			var newUser string

			if conf.UserVariable == "" {
				newUser = user
			} else {
				// translate with user variable to get newUser
				newUserVar, ok := row.Data[conf.UserVariable]

				if !ok {
					errs = append(errs, fmt.Errorf("Could not find user variable %s for user previously known as %s", conf.UserVariable, user))
					continue
				}

				// hope the user variable is a string...
				// if not, make it one???
				// make simple UnmarshalAsString func
				err := json.Unmarshal(newUserVar.Value, &newUser)

				if err != nil {
					errs = append(errs, err)
				}
			}

			// First time we see a new user, make a Row
			_, ok := infData[newUser]
			if !ok {
				idv := make(map[string]*InferenceDataValue)
				infData[newUser] = &InferenceDataRow{User: newUser, Data: idv}
			}

			// Add all data to the user
			for v, val := range row.Data {
				infData[newUser].Data[v] = val
			}
		}
	}

	return infData, errs
}

// TODO: need to differentiate between bad errors and skip e

func Reduce(events []*InferenceDataEvent, c *InferenceDataConf) (InferenceData, []error, error) {
	intermediateData := make(IntermediateInferenceData)
	extractionErrors := []error{}

	for _, e := range events {

		sourceConf, ok := c.DataSources[e.SourceConf.Name]

		if !ok {
			return nil, extractionErrors, fmt.Errorf("Attempted to process event from data source not in SourceVariableMapping. "+
				"Data source: %s. Sources in mapping: %s",
				e.SourceConf.Name,
				c.Sources())
		}

		// add from metadata
		var err error
		intermediateData, err = extractValue(intermediateData, e, sourceConf.ExtractionConfs)
		if err != nil {
			extractionErrors = append(extractionErrors, err)
			continue
		}

	}

	// create intermediate datastructure, with user > source > variable > value
	// add step to join sources within each user, taking some config
	// (which points to the "user" (join) value for each source)

	res, errs := JoinSources(intermediateData, c.DataSources)
	for _, err := range errs {
		extractionErrors = append(extractionErrors, err)
	}

	return res, extractionErrors, nil
}
