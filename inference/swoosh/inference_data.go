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
	// Note that there is no "ad" location and there never really was one: the
	// ad-derived token lives in metadata, so reading it is an ordinary metadata
	// read. What makes it ad-derived is Mapping, below. The old "ad" value is
	// removed; see getRetrieveFunc.
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
	// value itself, for "ad_table_lookup" it addresses the token. The token's
	// location is never hardcoded — fly stamps it at metadata.vt by convention
	// and the conf says key: "vt" to match, so a platform surfacing it under
	// some other key just declares that key.
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
// It requires the metadata location as well as the mapping, because a lookup on
// any other location is incoherent and must not be treated as one. The danger
// is specifically tokenLookupKey: a `variable` conf carrying the lookup mapping
// would otherwise have its Key read as a declaration of where the token lives,
// and every respondent in the study would then be classified against the wrong
// metadata key — reported as organic, which does not alarm. Config-time
// validation rejects the combination (adopt/adopt/study_conf.py); this is the
// belt to that pair of braces, and getRetrieveFunc errors on it besides.
func isAdTableLookup(conf *ExtractionConf) bool {
	return conf.Mapping == MappingAdTableLookup && conf.Location == "metadata"
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

// retrieveFromMetadata reads User.Metadata[conf.Key] and then does whatever the
// conf's mapping says to do with what it read.
//
// For "raw" that is nothing — the value read is the answer, which is what every
// metadata conf ever written means. For "ad_table_lookup" the value read is an
// opaque token, and the answer is a stratum variable off the frozen
// ad_attributions row that token identifies:
//
//	metadata[key]              the token          (key = where to read)
//	attributions.ByRefToken[…] the frozen row     (the only automatic step)
//	row.Metadata[name]         the answer         (name = which stratum var)
//
// The mapping is closed over rather than looked up per call: RetrieveFunc has no
// context and no error and runs once per event per conf, so a database call in
// here would be one query per response. It is loaded once per study in
// swooshStudy and passed down as plain data, which is also what keeps Reduce
// pure and unit-testable against a fake mapping.
//
// There is deliberately no fallback. A token that resolves to no row returns
// ok=false and is counted as unmapped by adAttributionOutcome; it is never
// retried as a raw value, and never retried against ad_id.
func retrieveFromMetadata(attributions AdAttributions) RetrieveFunc {
	return func(e *InferenceDataEvent, conf *ExtractionConf) (json.RawMessage, bool) {
		v, ok := e.User.Metadata[conf.Key]
		if !ok {
			return nil, false
		}

		if !isAdTableLookup(conf) {
			return v, true
		}

		token, ok := metadataToken(v)
		if !ok {
			return nil, false
		}

		a, ok := attributions.ByRefToken[token]
		if !ok {
			return nil, false
		}

		// conf.Name, not conf.Key: for a lookup, Key addressed the token and
		// Name addresses the stratum variable on the row.
		val, ok := a.Metadata[conf.Name]
		return val, ok
	}
}

// metadataToken reads a metadata value as the join token.
//
// The unquoting is the point. Metadata values are JSON, so the token fly stamps
// arrives here as a quoted JSON string (`"a1b2c3d4e5"`) while
// ad_attributions.ref_token is scanned out of a text column unquoted
// (`a1b2c3d4e5`). Joining the raw bytes against the map would therefore miss
// every single time, on a value that looks correct in every log line it appears
// in — the exact silent-miscount failure this whole design exists to prevent.
//
// A value that is not a JSON string is not a token: it yields nothing rather
// than a best-effort stringification, so the event lands in unmapped, where
// someone can see it.
func metadataToken(raw json.RawMessage) (string, bool) {
	var token string
	if err := json.Unmarshal(raw, &token); err != nil {
		return "", false
	}
	if token == "" {
		return "", false
	}
	return token, true
}

func retrieveFromVariable(e *InferenceDataEvent, conf *ExtractionConf) (json.RawMessage, bool) {
	if conf.Key == "*" {
		return e.Value, true
	}
	ok := e.Variable == conf.Key
	return e.Value, ok
}

func getRetrieveFunc(conf *ExtractionConf, attributions AdAttributions) (RetrieveFunc, error) {
	switch conf.Location {
	case "variable":
		if conf.Mapping == MappingAdTableLookup {
			// Incoherent rather than merely useless: see isAdTableLookup. Loud,
			// because silently degrading it to a raw variable read would leave
			// the study half-configured and counting wrong.
			return nil, fmt.Errorf(
				`conf %q declares mapping %q on location "variable"; the ad token lives in metadata, so a lookup is only valid on location "metadata"`,
				conf.Name, MappingAdTableLookup)
		}
		return retrieveFromVariable, nil
	case "metadata":
		return retrieveFromMetadata(attributions), nil
	}

	return nil, fmt.Errorf("Could not find location function for location: %s", conf.Location)
}

// Entities for the two ad-attribution outcomes worth counting. They follow the
// existing `<kind>=<name>` convention (see "var=" and "source=") so that
// recordExtractionError can route them by prefix.
const (
	entityAdOrganic  = "ad=organic"
	entityAdUnmapped = "ad=unmapped"
)

// mechanismRefToken names the attribution mechanism in every outcome's details,
// so that a miss recorded in study_run_events says what it was trying to join
// on rather than leaving the reader to infer it from the era of the row.
const mechanismRefToken = "ref_token"

// tokenLookupKey reports the metadata key this source's ad_table_lookup confs
// read their token from, and whether the source declares any such conf at all.
//
// One respondent has one token, in one place, so every ad_table_lookup conf
// under a source must agree on where it is. That agreement is a config-time
// check (adopt's study conf validation); here we take the first declared key on
// the understanding that they match. Taking the first rather than erroring on
// disagreement is deliberate: swoosh recomputes whole studies unattended, and
// refusing to classify would cost a study its counts over a conf problem this
// run cannot fix anyway.
func tokenLookupKey(confs []*ExtractionConf) (string, bool) {
	for _, c := range confs {
		if isAdTableLookup(c) {
			return c.Key, true
		}
	}
	return "", false
}

// adAttributionOutcome classifies one event against the study's mapping.
//
// A retrieve returning ok=false means `continue`: no variable, no stratum match,
// optimizer undercount. Two very different things produce that, and telling them
// apart is the whole point of this function:
//
//	attributed — token present, mapping row found        → normal, no event
//	organic    — no token on the event                   → expected; count, don't alarm
//	unmapped   — token present, no mapping row           → always a bug; alert
//
// Classification is per *event*, not per conf. An event either carries a token
// or it does not, and that token either resolves or it does not — none of which
// depends on the conf. Counting it per conf would multiply one organic arrival
// by however many ad_table_lookup confs the study happens to declare.
//
// The mechanism is ref_token, and only ref_token. A token that resolves to
// nothing is unmapped; it is never quietly retried against the event's ad_id.
// ad_id is still carried on the event and reported in the details below, but
// purely so a miss can be cross-referenced against recruitment-health alerting
// — it is not a second attribution path, because a fallback would make a real
// miss indistinguishable from a study part-way through switching mechanisms.
//
// Returns nil when the source declares no ad_table_lookup confs at all, so
// studies on the plain `mapping: "raw"` path are entirely unaffected.
func adAttributionOutcome(e *InferenceDataEvent, confs []*ExtractionConf, attributions AdAttributions) *ExtractionError {
	key, ok := tokenLookupKey(confs)
	if !ok {
		return nil
	}

	token, ok := metadataToken(e.User.Metadata[key])
	if !ok {
		return &ExtractionError{
			Entity: entityAdOrganic,
			Message: fmt.Sprintf(
				"respondent %s arrived with no ref token at metadata.%s and is not attributed to any stratum",
				e.User.ID, key),
			Count: 1,
			Details: map[string]interface{}{
				"source":    e.SourceConf.Name,
				"mechanism": mechanismRefToken,
				"token_key": key,
			},
		}
	}

	if _, ok := attributions.ByRefToken[token]; !ok {
		return &ExtractionError{
			Entity: entityAdUnmapped,
			Message: fmt.Sprintf(
				"ref token %s (read from metadata.%s) has no ad_attributions row for this study; respondent %s is not attributed to any stratum",
				token, key, e.User.ID),
			Count: 1,
			Details: map[string]interface{}{
				"source":    e.SourceConf.Name,
				"mechanism": mechanismRefToken,
				"ref_token": token,
				"token_key": key,
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
//     those events are indistinguishable from organic arrivals, so they would
//     land in the do-not-alarm bucket.
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
		// `continue` on it: organic and unmapped are counts, not failures. An
		// unmapped event may still carry perfectly good `variable` confs, and
		// dropping those would turn a missing mapping row into missing survey
		// data too.
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
