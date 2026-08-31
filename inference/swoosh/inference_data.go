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
	// Location is where to read from: "metadata" or "variable".
	//
	// It says where a value is and nothing about what the value means — that is
	// Mapping, below. So a lookup reads its token from either location: a
	// respondent recruited by a fly destination brings the token back in event
	// metadata, and one recruited by a web or app destination lands on the
	// researcher's own page and brings it back as a survey field.
	Location string `json:"location"`

	// Mapping says what to do with the value Location produced.
	//
	//	"" / "raw"        the value read IS the answer. The historical
	//	                  behaviour, and the default, so every conf ever
	//	                  written keeps meaning exactly what it meant.
	//	"ad_table_lookup" the value read is an opaque token; the answer is a
	//	                  stratum variable off the frozen ad_attributions row
	//	                  that token identifies.
	//
	// It is a property of the study's configuration, fixed when the study is
	// configured — never a runtime choice made by sniffing which key an event
	// happens to carry. A runtime choice would make a genuine miss (a token
	// with no row, which is always a bug) indistinguishable from a study
	// switching mechanisms, and there is deliberately no fallback between the
	// two. See adAttributionOutcome.
	Mapping string `json:"mapping,omitempty"`

	// Key is WHERE TO READ, contextual to Mapping: for "raw" it addresses the
	// value itself, for "ad_table_lookup" it addresses the token. Where the
	// token lives is never hardcoded — fly stamps it at metadata.vt by
	// convention and the conf says location "metadata", key "vt" to match. A
	// platform that surfaces it elsewhere declares that place instead, and two
	// lookup confs under one source need not agree on it.
	Key string `json:"key"`

	// Name is the output variable name and, for "ad_table_lookup", ALSO the key
	// into the frozen row's metadata — i.e. which stratum variable to pull. It
	// does double duty because you name the output after the stratum variable
	// it pulls anyway. This is the one constraint the mapping design carries.
	Name string `json:"name"`

	Functions []ExtractionFunctionConf `json:"functions"`
	ValueType string                   `json:"value_type"`
	Aggregate string                   `json:"aggregate"` // first, last, max, min
	fns       []ExtractionFunction
}

// The values Mapping takes.
//
// MappingRaw is also what the empty string means, so confs written before the
// field existed keep working untouched — which is the whole reason the default
// is the historical behaviour rather than the new one.
const (
	MappingRaw           = "raw"
	MappingAdTableLookup = "ad_table_lookup"
)

// isAdTableLookup reports whether this conf resolves through the ad table.
//
// The mapping alone decides it. Location says only where to read, and
// resolveThroughAdTable wraps whichever reader that names, so a lookup is as
// valid on a Typeform field as on fly's event metadata.
func isAdTableLookup(conf *ExtractionConf) bool {
	return conf.Mapping == MappingAdTableLookup
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

// retrieveFromMetadata reads User.Metadata[conf.Key] — the key fly stamped its
// value under.
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

// locationReader returns the reader for a location. Location is where to read
// and nothing else, so this knows nothing about mappings.
func locationReader(location string) (RetrieveFunc, error) {
	switch location {
	case "variable":
		return retrieveFromVariable, nil
	case "metadata":
		return retrieveFromMetadata, nil
	}

	return nil, fmt.Errorf("Could not find location function for location: %s", location)
}

// resolveThroughAdTable turns a reader of raw values into a reader of stratum
// variables, by treating what it read as an ad token:
//
//	read(e, conf)               the token          (Key = where to read)
//	attributions.ByRefToken[…]  the frozen row     (the only automatic step)
//	row.Metadata[conf.Name]     the answer         (Name = which stratum var)
//
// It wraps any reader, which is what lets one study attribute respondents who
// arrive by different routes. A respondent recruited by a fly destination
// brings the token back in event metadata; one recruited by a web or app
// destination lands on the researcher's own page and brings it back as a
// Typeform or Qualtrics field. Each conf declares where its own token is.
//
// The mapping is closed over rather than looked up per call: RetrieveFunc has
// no context and no error and runs once per event per conf, so a database call
// in here would be one query per response. It is loaded once per study in
// swooshStudy and passed down as plain data, which is also what keeps Reduce
// pure and unit-testable against a fake mapping.
//
// There is deliberately no fallback. A token that resolves to no row returns
// ok=false and is counted as unmapped by adAttributionOutcome; it is never
// retried as a raw value, and never retried against ad_id.
func resolveThroughAdTable(read RetrieveFunc, attributions AdAttributions) RetrieveFunc {
	return func(e *InferenceDataEvent, conf *ExtractionConf) (json.RawMessage, bool) {
		raw, ok := read(e, conf)
		if !ok {
			return nil, false
		}

		token, ok := refToken(raw)
		if !ok {
			return nil, false
		}

		a, ok := attributions.ByRefToken[token]
		if !ok {
			return nil, false
		}

		// conf.Name, not conf.Key: Key addressed the token and Name addresses
		// the stratum variable on the row.
		val, ok := a.Metadata[conf.Name]
		return val, ok
	}
}

// refToken reads an extracted value as the join token.
//
// The unquoting is the point. Extracted values are JSON, so the token arrives
// here as a quoted JSON string (`"a1b2c3d4e5"`) while ad_attributions.ref_token
// is scanned out of a text column unquoted (`a1b2c3d4e5`). swoosh compares the
// extracted value to ref_token verbatim, so joining the raw bytes would miss
// every single time, on a value that looks correct in every log line it appears
// in — the exact silent-miscount failure this whole design exists to prevent.
//
// A value that is not a JSON string is not a token: it yields nothing rather
// than a best-effort stringification that would match nothing while reading
// correctly.
func refToken(raw json.RawMessage) (string, bool) {
	var token string
	if err := json.Unmarshal(raw, &token); err != nil {
		return "", false
	}
	if token == "" {
		return "", false
	}
	return token, true
}

// getRetrieveFunc composes the two halves of a conf: the location says where to
// read, and the mapping says what the value read means. A lookup is the
// location's reader wrapped in resolveThroughAdTable.
func getRetrieveFunc(conf *ExtractionConf, attributions AdAttributions) (RetrieveFunc, error) {
	read, err := locationReader(conf.Location)
	if err != nil {
		return nil, err
	}

	if isAdTableLookup(conf) {
		return resolveThroughAdTable(read, attributions), nil
	}

	return read, nil
}

// entityAdUnmapped is the one ad-attribution outcome worth reporting. It
// follows the existing `<kind>=<name>` convention (see "var=" and "source=") so
// that recordExtractionError can route it by prefix.
const entityAdUnmapped = "ad=unmapped"

// mechanismRefToken names the attribution mechanism in every outcome's details,
// so that a miss recorded in study_run_events says what it was trying to join
// on rather than leaving the reader to infer it from the era of the row.
const mechanismRefToken = "ref_token"

// adAttributionOutcome reports the one ad-attribution outcome worth reporting:
// a token that resolves to no ad_attributions row for this study.
//
// Whatever the cause, the effect on this study is the same — a retrieve
// returning ok=false means `continue`: no variable, no stratum match, and a
// respondent missing from stratum counts. It does not error, it miscounts,
// which is why it is reported at all.
//
// It is reported at severity *warning*, not error, because the two causes are
// not both bugs: the token may belong to another study sharing this survey,
// in which case declining it is the mechanism working. classifyExtractionError
// carries that reasoning and the cost of not separating them.
//
// An event carrying no token produces nothing. That is an expected arrival, not
// a failure: shortcodes are shareable by design, and a study can perfectly well
// recruit people who never clicked an ad.
//
// The walk asks each lookup conf through its own locationReader, because each
// conf declares where its own token is and two confs under one source need not
// agree. It returns on the first token that does not resolve, so one event
// yields at most one outcome however many lookup confs a study declares —
// counting per conf would multiply one miss by the size of the conf list.
//
// The mechanism is ref_token, and only ref_token. A token that resolves to
// nothing is unmapped; it is never quietly retried against the event's ad_id.
// ad_id is still carried on the event and reported in the details below, but
// purely so a miss can be cross-referenced against recruitment-health alerting
// — it is not a second attribution path, because a fallback would make a real
// miss indistinguishable from a study part-way through switching mechanisms.
func adAttributionOutcome(e *InferenceDataEvent, confs []*ExtractionConf, attributions AdAttributions) *ExtractionError {
	for _, conf := range confs {
		if !isAdTableLookup(conf) {
			continue
		}

		read, err := locationReader(conf.Location)
		if err != nil {
			// An unknown location reads nothing, so there is no token to
			// classify. extractValue reports the conf itself, under var=.
			continue
		}

		raw, ok := read(e, conf)
		if !ok {
			continue
		}

		token, ok := refToken(raw)
		if !ok {
			continue
		}

		if _, ok := attributions.ByRefToken[token]; ok {
			continue
		}

		return &ExtractionError{
			Entity: entityAdUnmapped,
			Message: fmt.Sprintf(
				"ref token %s (read from %s %s) has no ad_attributions row for this study; respondent %s is not attributed to any stratum",
				token, conf.Location, conf.Key, e.User.ID),
			Count: 1,
			Details: map[string]interface{}{
				"source":         e.SourceConf.Name,
				"mechanism":      mechanismRefToken,
				"ref_token":      token,
				"token_key":      conf.Key,
				"token_location": conf.Location,
				// Captured, not joined — here only so a miss can be lined up
				// against fly's recruitment-health signals.
				"ad_id":             e.AdID,
				"ad_network":        e.AdNetwork,
				"tokens_in_mapping": attributions.Len(),
			},
		}
	}

	return nil
}

// extractValue applies each ExtractionConf to one event. On failure it returns
// an *ExtractionError keyed by the offending variable (conf.Name) so callers can
// aggregate per entity; the event's remaining confs are skipped (first failure
// wins), matching the previous behaviour.
func extractValue(id IntermediateInferenceData, e *InferenceDataEvent, extractionConfs []*ExtractionConf, attributions AdAttributions) (IntermediateInferenceData, *ExtractionError) {

	for _, conf := range extractionConfs {
		retrieve, err := getRetrieveFunc(conf, attributions)
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

// Reduce folds a study's whole event history into InferenceData.
//
// `attributions` is the study's frozen ad -> stratum mapping, passed in as
// plain data so that Reduce stays pure and can be tested against a fake mapping;
// the database read lives in swooshStudy. An empty mapping is fine and means
// "this study has no ad mapping", which is the correct state for every study on
// the plain `mapping: "raw"` path.
//
// Note that swoosh recomputes a study's entire history on every run — GetEvents
// loads every event and InsertInferenceData upserts. Two consequences worth
// keeping in mind:
//
//   - `mapping: "ad_table_lookup"` is for new studies only, and there is
//     deliberately no fallback to the raw metadata value. Swapping an existing
//     study's confs over would not migrate it forward, it would retroactively
//     re-attribute its entire back-catalogue through a path those events cannot
//     satisfy: rows written before the study's ads carried an encoded ref have
//     no token and are never backfilled, so every historical respondent would
//     extract nothing, match no stratum, and vanish from the counts. Worse,
//     an event carrying no token is an expected arrival, so none of it would
//     even be reported.
//   - unmapped is self-healing. Inserting a missing mapping row retroactively
//     fixes every prior run's attribution, so the unmapped count is a
//     current-state measure and drops to zero on the next run after a fix.
func Reduce(events []*InferenceDataEvent, c *InferenceDataConf, attributions AdAttributions) (InferenceData, []ExtractionError, error) {
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

		// Classify the event's ad attribution before extracting, and do not
		// `continue` on it: unmapped is a count, not a failure. An unmapped
		// event may still carry perfectly good `variable` confs, and dropping
		// those would turn a missing mapping row into missing survey data too.
		if outcome := adAttributionOutcome(e, sourceConf.ExtractionConfs, attributions); outcome != nil {
			agg.add(*outcome)
		}

		// add from metadata
		var extErr *ExtractionError
		intermediateData, extErr = extractValue(intermediateData, e, sourceConf.ExtractionConfs, attributions)
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
