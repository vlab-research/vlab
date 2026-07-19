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
		id[source][user] = &InferenceDataRow{
			User: user,
			Data: make(map[string]*InferenceDataValue),
		}
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

// ExtractionError is a per-entity problem found while reducing events into
// InferenceData. Entity is a stable grouping key ("source=<name>" or
// "var=<name>") that the study_run_events writer uses as a fingerprint; Count
// is the number of raw occurrences folded into this error; Message is a
// human-readable sample (the first occurrence); Details carries structured
// context for the dashboard (e.g. sources_in_mapping for unmapped sources).
type ExtractionError struct {
	Entity  string
	Message string
	Count   int
	Details map[string]interface{}
}

func (e ExtractionError) Error() string { return e.Message }

// extractionErrorAgg aggregates ExtractionErrors by Entity so that one bad
// value per user across thousands of users produces a single error with a
// count, not thousands of near-identical errors.
type extractionErrorAgg struct {
	order    []string
	byEntity map[string]*ExtractionError
}

func newExtractionErrorAgg() *extractionErrorAgg {
	return &extractionErrorAgg{byEntity: map[string]*ExtractionError{}}
}

// add folds err into the aggregate. Repeated occurrences of the same entity
// bump Count; the first occurrence's Message/Details are kept as the sample.
// A zero Count means "one occurrence" (callers reporting a single error don't
// set it); it must be normalized before merging or it would add nothing.
func (a *extractionErrorAgg) add(err ExtractionError) {
	if err.Count <= 0 {
		err.Count = 1
	}
	if e, ok := a.byEntity[err.Entity]; ok {
		e.Count += err.Count
		return
	}
	a.byEntity[err.Entity] = &err
	a.order = append(a.order, err.Entity)
}

func (a *extractionErrorAgg) addAll(errs []ExtractionError) {
	for _, e := range errs {
		a.add(e)
	}
}

func (a *extractionErrorAgg) list() []ExtractionError {
	res := make([]ExtractionError, len(a.order))
	for i, k := range a.order {
		res[i] = *a.byEntity[k]
	}
	return res
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

// extractValue applies each ExtractionConf to one event. On failure it returns
// an *ExtractionError keyed by the offending variable (conf.Name) so callers can
// aggregate per entity; the event's remaining confs are skipped (first failure
// wins), matching the previous behaviour.
func extractValue(id IntermediateInferenceData, e *InferenceDataEvent, extractionConfs []*ExtractionConf) (IntermediateInferenceData, *ExtractionError) {

	for _, conf := range extractionConfs {
		retrieve, err := getRetrieveFunc(conf)
		if err != nil {
			return id, &ExtractionError{Entity: "var=" + conf.Name, Message: err.Error()}
		}

		val, ok := retrieve(e, conf)
		if !ok {
			continue
		}

		val, err = conf.Extract(val)
		if err != nil {
			return id, &ExtractionError{Entity: "var=" + conf.Name, Message: err.Error()}
		}

		v := &InferenceDataValue{
			Timestamp: e.Timestamp,
			Variable:  conf.Name,
			Value:     val,
			ValueType: conf.ValueType,
		}

		id, err = addValue(conf, id, e.User.ID, e.SourceConf.Name, v)
		if err != nil {
			return id, &ExtractionError{Entity: "var=" + conf.Name, Message: err.Error()}
		}
	}

	return id, nil
}

func JoinSources(intermediateData IntermediateInferenceData, confs map[string]*DataSource) (InferenceData, []ExtractionError) {

	agg := newExtractionErrorAgg()
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
					agg.add(ExtractionError{
						Entity:  "var=" + conf.UserVariable,
						Message: fmt.Sprintf("Could not find user variable %s for user previously known as %s", conf.UserVariable, user),
						Details: map[string]interface{}{"source": source},
					})
					continue
				}

				// hope the user variable is a string...
				// if not, make it one???
				// make simple UnmarshalAsString func
				err := json.Unmarshal(newUserVar.Value, &newUser)

				if err != nil {
					agg.add(ExtractionError{
						Entity:  "var=" + conf.UserVariable,
						Message: err.Error(),
						Details: map[string]interface{}{"source": source},
					})
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

	return infData, agg.list()
}

// TODO: need to differentiate between bad errors and skip e

func Reduce(events []*InferenceDataEvent, c *InferenceDataConf) (InferenceData, []ExtractionError, error) {
	intermediateData := make(IntermediateInferenceData)
	agg := newExtractionErrorAgg()

	for _, e := range events {

		sourceConf, ok := c.DataSources[e.SourceConf.Name]

		if !ok {
			// Skip events from unmapped sources, aggregated to one ExtractionError
			// per source name (Count = number of skipped events). Historical events
			// orphaned by mid-study source renames (e.g. "Fly" → "Fly HPV Double")
			// should not abort aggregation of mapped sources.
			agg.add(ExtractionError{
				Entity: "source=" + e.SourceConf.Name,
				Message: fmt.Sprintf(
					"data source not in SourceVariableMapping (skipped): %s. Sources in mapping: %s",
					e.SourceConf.Name,
					c.Sources()),
				Details: map[string]interface{}{
					"source":             e.SourceConf.Name,
					"sources_in_mapping": c.Sources(),
				},
			})
			continue
		}

		// add from metadata
		var extErr *ExtractionError
		intermediateData, extErr = extractValue(intermediateData, e, sourceConf.ExtractionConfs)
		if extErr != nil {
			agg.add(*extErr)
			continue
		}

	}

	// create intermediate datastructure, with user > source > variable > value
	// add step to join sources within each user, taking some config
	// (which points to the "user" (join) value for each source)

	res, joinErrs := JoinSources(intermediateData, c.DataSources)
	agg.addAll(joinErrs)

	return res, agg.list(), nil
}
