package main

// Ad attribution in swoosh: the read side of the encoded ref.
//
// vlab owns the ad -> stratum join. An extraction conf declaring
// `mapping: "ad_table_lookup"` reads an opaque token out of the respondent's
// metadata and resolves the variable through the frozen ad_attributions row
// that token identifies — instead of through the dotted stratum vocabulary that
// used to ride inside every message's ref.
//
// The token is the join key, and the *only* join key. ad_id was the earlier
// attempt at the same shape and is superseded: Meta sends the referral webhook
// carrying it for only ~31% of Messenger ad entrants, so the other 69% could
// never be joined. It is still captured on the event, and asserted below to be
// ignored — a fallback between the two mechanisms would make a real miss
// indistinguishable from a study part-way through switching.
//
// The failure mode all of this guards against is quiet: a retrieve returning
// ok=false means `continue` — no variable, no stratum match, optimizer
// undercount. It does not error, it miscounts. So these tests care as much
// about *which counter* an event lands in as about the value it produces.

import (
	"context"
	"encoding/json"
	"fmt"
	"testing"
	"time"

	"github.com/jackc/pgx/v4/pgxpool"
	"github.com/stretchr/testify/assert"
	. "github.com/vlab-research/vlab/inference/inference-data"
	. "github.com/vlab-research/vlab/inference/test-helpers"
)

// --------------------------------------------------------------------------
// helpers
// --------------------------------------------------------------------------

// tokenKey is where fly stamps the token. It is a convention, not a constant
// the join code knows: the conf declares it (see lookupConf), and a platform
// surfacing the token under another key would simply declare that one.
const tokenKey = "vt"

// tokenEvent is a respondent who arrived through an ad carrying an encoded ref.
//
// It sets an ad id as well as the token, because a real fly event carries both
// — and several tests below depend on the ad id being present and ignored.
func tokenEvent(user, token string, ts time.Time) *InferenceDataEvent {
	e := &InferenceDataEvent{
		User:       User{ID: user},
		SourceConf: &SourceConf{Name: "fly"},
		Timestamp:  ts,
		Variable:   "q1",
		Value:      json.RawMessage(`{"response": "yes"}`),
		AdID:       "ad-" + token,
		AdNetwork:  NetworkFacebook,
	}
	if token != "" {
		e.User.Metadata = map[string]json.RawMessage{
			tokenKey: json.RawMessage(fmt.Sprintf("%q", token)),
		}
	}
	return e
}

// organicEvent has no token, which is what an entrant who never clicked an ad
// looks like: someone who was given the shortcode directly, or arrived via a
// reshared page post.
func organicEvent(user string, ts time.Time) *InferenceDataEvent {
	e := tokenEvent(user, "", ts)
	e.AdID = ""
	e.AdNetwork = ""
	return e
}

// lookupConf declares one ad-derived variable.
//
// Note what each field means, because both are contextual to the mapping:
// `key` is where the TOKEN is read from, and `name` is both the output variable
// name and the stratum variable pulled off the frozen row. So this conf says
// "read the token at metadata.vt, and give me the row's `stratumVar` under that
// same name".
func lookupConf(stratumVar string) *ExtractionConf {
	return &ExtractionConf{
		Location:  "metadata",
		Mapping:   MappingAdTableLookup,
		Key:       tokenKey,
		Name:      stratumVar,
		ValueType: "categorical",
		Aggregate: "first",
		Functions: []ExtractionFunctionConf{
			{Function: "select", Params: []byte(`{"path": ""}`)},
		},
	}
}

// rawConf is the historical behaviour, and the default: the value read from
// metadata IS the answer.
func rawConf(key, name string) *ExtractionConf {
	return &ExtractionConf{
		Location:  "metadata",
		Key:       key,
		Name:      name,
		ValueType: "categorical",
		Aggregate: "first",
		Functions: []ExtractionFunctionConf{
			{Function: "select", Params: []byte(`{"path": ""}`)},
		},
	}
}

func confWith(confs ...*ExtractionConf) *InferenceDataConf {
	return &InferenceDataConf{map[string]*DataSource{
		"fly": {ExtractionConfs: confs},
	}}
}

func attribution(refToken, stratum string, md map[string]string) AdAttribution {
	raw := map[string]json.RawMessage{}
	for k, v := range md {
		b, err := json.Marshal(v)
		if err != nil {
			panic(err)
		}
		raw[k] = b
	}
	return AdAttribution{
		AdID:     "ad-" + refToken,
		Network:  NetworkFacebook,
		Stratum:  stratum,
		Metadata: raw,
		RefToken: refToken,
	}
}

// loadedMapping builds the study's loaded attributions, indexed the one way
// anything is ever allowed to join on them.
func loadedMapping(attrs ...AdAttribution) AdAttributions {
	a := NewAdAttributions()
	for _, at := range attrs {
		a.ByRefToken[at.RefToken] = at
	}
	return a
}

func errorsByEntity(errs []ExtractionError) map[string]ExtractionError {
	m := map[string]ExtractionError{}
	for _, e := range errs {
		m[e.Entity] = e
	}
	return m
}

// --------------------------------------------------------------------------
// the ad_table_lookup mapping
// --------------------------------------------------------------------------

func TestReduce_LookupResolvesThroughTheFrozenRow(t *testing.T) {
	// The whole point: the value comes off the row the token identifies, not
	// from anything the respondent said and not from the metadata value itself.
	events := []*InferenceDataEvent{tokenEvent("u1", "a1b2c3d4e5", ti("07"))}

	attributions := loadedMapping(attribution("a1b2c3d4e5", "stratum-1", map[string]string{
		"creative": "Smiling",
		"gender":   "women",
		"form":     "mnchweek",
	}))

	actual, errs, err := Reduce(events, confWith(lookupConf("gender")), attributions)

	assert.Nil(t, err)
	assert.Len(t, errs, 0)
	assert.Equal(t, InferenceData{
		"u1": {User: "u1", Data: map[string]*InferenceDataValue{
			"gender": {
				Timestamp: ti("07"),
				Variable:  "gender",
				Value:     []byte(`"women"`),
				ValueType: "categorical",
			},
		}},
	}, actual)
}

func TestReduce_NameIsBothTheOutputNameAndTheRowKey(t *testing.T) {
	// The one constraint the mapping design carries, pinned explicitly: for a
	// lookup, `name` does double duty. `key` addressed the token; `name` says
	// which stratum variable to pull AND what to call it.
	events := []*InferenceDataEvent{tokenEvent("u1", "tok", ti("07"))}

	attributions := loadedMapping(attribution("tok", "stratum-1", map[string]string{
		"gender": "women",
		"Age":    "25_34",
	}))

	actual, _, err := Reduce(events, confWith(lookupConf("Age")), attributions)

	assert.Nil(t, err)
	assert.Equal(t, []byte(`"25_34"`), []byte(actual["u1"].Data["Age"].Value),
		"name selected the row key AND named the output")
	assert.NotContains(t, actual["u1"].Data, "gender",
		"only the declared stratum variable comes out")
}

func TestReduce_LookupResolvesCreativeAndFormKeys(t *testing.T) {
	// `creative` and `form` are the two keys that only exist because the frozen
	// blob is the ref's dict rather than stratum.metadata (see the invariant in
	// adopt/adopt/test_marketing.py). If the mapping were built from the stratum
	// conf, these two would resolve to nothing.
	events := []*InferenceDataEvent{tokenEvent("u1", "tok", ti("07"))}

	attributions := loadedMapping(attribution("tok", "stratum-1", map[string]string{
		"creative": "Smiling",
		"form":     "mnchweek",
	}))

	actual, errs, err := Reduce(
		events,
		confWith(lookupConf("creative"), lookupConf("form")),
		attributions,
	)

	assert.Nil(t, err)
	assert.Len(t, errs, 0)
	assert.Equal(t, []byte(`"Smiling"`), []byte(actual["u1"].Data["creative"].Value))
	assert.Equal(t, []byte(`"mnchweek"`), []byte(actual["u1"].Data["form"].Value))
}

func TestReduce_TheTokenKeyComesFromTheConfNotFromAConstant(t *testing.T) {
	// The join code never assumes metadata.vt. fly stamps `vt` by convention and
	// the conf says so; a platform producing the token under another key just
	// declares that key, with no structural change anywhere.
	e := tokenEvent("u1", "tok", ti("07"))
	e.User.Metadata = map[string]json.RawMessage{"some_other_key": []byte(`"tok"`)}

	conf := lookupConf("gender")
	conf.Key = "some_other_key"

	attributions := loadedMapping(attribution("tok", "stratum-1", map[string]string{"gender": "women"}))

	actual, errs, err := Reduce([]*InferenceDataEvent{e}, confWith(conf), attributions)

	assert.Nil(t, err)
	assert.Len(t, errs, 0)
	assert.Equal(t, []byte(`"women"`), []byte(actual["u1"].Data["gender"].Value))
}

func TestReduce_LookupDoesNotFallBackToTheRawValue(t *testing.T) {
	// There is deliberately no fallback. A lookup conf is for new studies only;
	// falling back to the raw value would let someone swap an existing study's
	// confs and silently re-attribute its whole back-catalogue through a path
	// its events cannot satisfy, because swoosh recomputes all history each run.
	//
	// Here the token reads as a perfectly good literal value and the mapping does
	// not have it. Nothing must come out.
	e := tokenEvent("u1", "women", ti("07"))

	actual, errs, err := Reduce(
		[]*InferenceDataEvent{e},
		confWith(lookupConf("gender")),
		NewAdAttributions(),
	)

	assert.Nil(t, err)
	assert.Empty(t, actual, "the raw metadata value must not be used as the answer")

	// ...and it is reported as unmapped rather than passing silently.
	assert.Contains(t, errorsByEntity(errs), entityAdUnmapped)
}

func TestReduce_AdIDIsCapturedButNeverJoinedOn(t *testing.T) {
	// ad_id is deprecated as a join. The event carries one, and the study's
	// mapping holds the very row that ad id belongs to — but the respondent has
	// no token, so they are organic. Anything else would be a runtime fallback
	// between mechanisms, which is exactly what the design forbids: it would
	// make a genuine miss indistinguishable from a mechanism switch.
	e := organicEvent("u1", ti("07"))
	e.AdID = "ad-tok"
	e.AdNetwork = NetworkFacebook

	attributions := loadedMapping(attribution("tok", "stratum-1", map[string]string{"gender": "women"}))

	actual, errs, err := Reduce([]*InferenceDataEvent{e}, confWith(lookupConf("gender")), attributions)

	assert.Nil(t, err)
	assert.Empty(t, actual, "a matching ad_id must not attribute anybody")
	assert.Contains(t, errorsByEntity(errs), entityAdOrganic,
		"no token is organic, regardless of what ad_id says")
}

func TestReduce_RawMappingIsUnaffectedByAttributions(t *testing.T) {
	// Existing studies keep raw metadata confs forever and must be completely
	// untouched by any of this — including by the zero-value mapping, which has
	// a nil index.
	e := organicEvent("u1", ti("07"))
	e.User.Metadata = map[string]json.RawMessage{"gender": []byte(`"women"`)}

	actual, errs, err := Reduce(
		[]*InferenceDataEvent{e},
		confWith(rawConf("gender", "md:gender")),
		AdAttributions{},
	)

	assert.Nil(t, err)
	assert.Len(t, errs, 0, "a raw-mapping study must produce no ad outcomes at all")
	assert.Equal(t, []byte(`"women"`), []byte(actual["u1"].Data["md:gender"].Value))
}

func TestReduce_ExplicitRawMappingMeansTheSameAsTheDefault(t *testing.T) {
	// "" and "raw" are the same thing, which is what lets every conf written
	// before the field existed keep meaning what it meant.
	e := organicEvent("u1", ti("07"))
	e.User.Metadata = map[string]json.RawMessage{"gender": []byte(`"women"`)}

	conf := rawConf("gender", "md:gender")
	conf.Mapping = MappingRaw

	actual, errs, err := Reduce([]*InferenceDataEvent{e}, confWith(conf), AdAttributions{})

	assert.Nil(t, err)
	assert.Len(t, errs, 0)
	assert.Equal(t, []byte(`"women"`), []byte(actual["u1"].Data["md:gender"].Value))
}

func TestReduce_TakesTheMappingAsDataSoLookupsCostNothingPerEvent(t *testing.T) {
	// Reduce has no *pgxpool.Pool in its signature and retrieveFromMetadata
	// closes over a plain map, so a per-event database call is not merely
	// avoided, it is unrepresentable. The mapping is loaded exactly once per
	// study, in swooshStudy, and passed down. If anyone moves the load into the
	// RetrieveFunc — which runs once per event per conf — this test stops
	// compiling, which is the point.
	events := []*InferenceDataEvent{}
	for i := 0; i < 1000; i++ {
		events = append(events, tokenEvent(fmt.Sprintf("u%d", i), "tok", ti("07")))
	}

	attributions := loadedMapping(attribution("tok", "stratum-1", map[string]string{"gender": "women"}))

	actual, errs, err := Reduce(events, confWith(lookupConf("gender")), attributions)

	assert.Nil(t, err)
	assert.Len(t, errs, 0)
	assert.Len(t, actual, 1000)
}

func TestGetRetrieveFunc_LocationAdIsRemoved(t *testing.T) {
	// The deprecated ad_id join. It must fail loudly and name its replacement,
	// rather than silently resolving to nothing.
	conf := &ExtractionConf{Location: "ad", Key: "gender", Name: "md:gender"}

	_, err := getRetrieveFunc(conf, NewAdAttributions())

	assert.NotNil(t, err)
	assert.Contains(t, err.Error(), MappingAdTableLookup,
		"the error must point at the mapping that replaced it")
}

// --------------------------------------------------------------------------
// the three-way split
// --------------------------------------------------------------------------

func TestReduce_AttributedProducesNoOutcomeEvent(t *testing.T) {
	events := []*InferenceDataEvent{tokenEvent("u1", "tok", ti("07"))}
	attributions := loadedMapping(attribution("tok", "stratum-1", map[string]string{"gender": "women"}))

	_, errs, err := Reduce(events, confWith(lookupConf("gender")), attributions)

	assert.Nil(t, err)
	assert.Len(t, errs, 0, "a normally attributed respondent is not an event")
}

func TestReduce_OrganicIsCountedButNotAnError(t *testing.T) {
	// Expected, not a bug: shortcodes are shareable by design and a Page linked
	// to a WhatsApp number gets a public button. Worth counting — a jump in the
	// organic share means a leaked shortcode — but it must not alarm.
	events := []*InferenceDataEvent{
		organicEvent("u1", ti("07")),
		organicEvent("u2", ti("08")),
	}

	_, errs, err := Reduce(events, confWith(lookupConf("gender")), NewAdAttributions())

	assert.Nil(t, err)
	byEntity := errorsByEntity(errs)

	organic, ok := byEntity[entityAdOrganic]
	assert.True(t, ok, "organic arrivals must be counted")
	assert.Equal(t, 2, organic.Count)
	assert.NotContains(t, byEntity, entityAdUnmapped, "organic is not unmapped")

	// And it is routed as a warning, never an error.
	eventType, severity := classifyExtractionError(entityAdOrganic)
	assert.Equal(t, eventExtractionWarning, eventType)
	assert.Equal(t, severityWarning, severity)
}

func TestReduce_UnmappedTokenIsACountedError(t *testing.T) {
	// Always a bug: vlab minted a token and failed to record what it meant.
	// Every respondent it recruits is dropped from stratum counts.
	events := []*InferenceDataEvent{
		tokenEvent("u1", "unknown", ti("07")),
		tokenEvent("u2", "unknown", ti("08")),
		tokenEvent("u3", "other-unknown", ti("09")),
	}

	_, errs, err := Reduce(events, confWith(lookupConf("gender")), NewAdAttributions())

	assert.Nil(t, err)
	byEntity := errorsByEntity(errs)

	unmapped, ok := byEntity[entityAdUnmapped]
	assert.True(t, ok, "a token with no mapping row must be reported")
	assert.Equal(t, 3, unmapped.Count, "aggregated per entity, one error with a count")
	assert.NotContains(t, byEntity, entityAdOrganic, "a token present is not organic")

	// The miss must be diagnosable: which mechanism, which key, which token.
	// Aggregation keeps the first event's message and details as the sample and
	// only accumulates Count, so this is u1's token, not u3's.
	assert.Equal(t, mechanismRefToken, unmapped.Details["mechanism"])
	assert.Equal(t, tokenKey, unmapped.Details["token_key"])
	assert.Equal(t, "unknown", unmapped.Details["ref_token"])
	assert.Contains(t, unmapped.Message, "ref token unknown")
	assert.Contains(t, unmapped.Message, "metadata.vt")

	// This is the one outcome that alarms.
	eventType, severity := classifyExtractionError(entityAdUnmapped)
	assert.Equal(t, eventExtractionError, eventType)
	assert.Equal(t, severityError, severity)
}

func TestReduce_ANonStringTokenIsUnmappedNotStringified(t *testing.T) {
	// Metadata values are JSON. A token that is not a JSON string is not a
	// token, and yields nothing rather than a best-effort stringification that
	// would match nothing while looking right in the logs.
	e := tokenEvent("u1", "tok", ti("07"))
	e.User.Metadata = map[string]json.RawMessage{tokenKey: []byte(`12345`)}

	attributions := loadedMapping(attribution("12345", "stratum-1", map[string]string{"gender": "women"}))

	actual, errs, err := Reduce([]*InferenceDataEvent{e}, confWith(lookupConf("gender")), attributions)

	assert.Nil(t, err)
	assert.Empty(t, actual)
	assert.Contains(t, errorsByEntity(errs), entityAdOrganic,
		"an unreadable token is no token at all")
}

func TestReduce_TheTokenIsJoinedUnquoted(t *testing.T) {
	// The unquoting that makes the join work at all. The token arrives as a
	// quoted JSON string in metadata; ref_token comes out of a text column
	// unquoted. Joining the raw bytes would miss every time, on a value that
	// looks correct in every log line it appears in.
	events := []*InferenceDataEvent{tokenEvent("u1", "a1b2c3d4e5", ti("07"))}

	// Keyed by the bare token, exactly as GetAdAttributions indexes it.
	attributions := loadedMapping(attribution("a1b2c3d4e5", "stratum-1", map[string]string{"gender": "women"}))

	actual, errs, err := Reduce(events, confWith(lookupConf("gender")), attributions)

	assert.Nil(t, err)
	assert.Len(t, errs, 0)
	assert.Equal(t, []byte(`"women"`), []byte(actual["u1"].Data["gender"].Value))
}

func TestReduce_SplitsAllThreeWaysInOneRun(t *testing.T) {
	events := []*InferenceDataEvent{
		tokenEvent("attributed", "tok", ti("07")),
		organicEvent("organic", ti("08")),
		tokenEvent("unmapped", "nope", ti("09")),
	}

	attributions := loadedMapping(attribution("tok", "stratum-1", map[string]string{"gender": "women"}))

	actual, errs, err := Reduce(events, confWith(lookupConf("gender")), attributions)

	assert.Nil(t, err)
	byEntity := errorsByEntity(errs)

	assert.Equal(t, 1, byEntity[entityAdOrganic].Count)
	assert.Equal(t, 1, byEntity[entityAdUnmapped].Count)

	// Only the attributed respondent produces a variable. The other two are
	// counted, not guessed at.
	assert.Len(t, actual, 1)
	assert.Contains(t, actual, "attributed")
}

func TestReduce_OrganicIsCountedOncePerEventNotOncePerConf(t *testing.T) {
	// Classification is a property of the event — it either carries a token or
	// it does not. Counting per conf would multiply one organic arrival by the
	// number of lookup confs the study happens to declare, which would make the
	// counter meaningless.
	events := []*InferenceDataEvent{organicEvent("u1", ti("07"))}

	conf := confWith(
		lookupConf("gender"),
		lookupConf("Age"),
		lookupConf("creative"),
	)

	_, errs, err := Reduce(events, conf, NewAdAttributions())

	assert.Nil(t, err)
	assert.Equal(t, 1, errorsByEntity(errs)[entityAdOrganic].Count,
		"one event, three lookup confs, one organic count")
}

func TestReduce_NoLookupConfsMeansNoAdOutcomesEvenWithoutTokens(t *testing.T) {
	// The guard that keeps every existing study silent. A study on the raw path
	// declares no lookup confs, so its events — which carry no token — must not
	// produce a flood of "organic" counts.
	e := organicEvent("u1", ti("07"))
	e.User.Metadata = map[string]json.RawMessage{"gender": []byte(`"women"`)}

	_, errs, err := Reduce(
		[]*InferenceDataEvent{e},
		confWith(rawConf("gender", "md:gender")),
		NewAdAttributions(),
	)

	assert.Nil(t, err)
	assert.Len(t, errs, 0)
}

func TestReduce_UnmappedTokenStillYieldsItsSurveyAnswers(t *testing.T) {
	// A missing mapping row must not also cost us the respondent's answers.
	// The ad-derived variable is lost (and counted); the `variable` conf is not.
	events := []*InferenceDataEvent{tokenEvent("u1", "nope", ti("07"))}

	conf := confWith(
		lookupConf("gender"),
		&ExtractionConf{
			Location: "variable", Key: "q1", Name: "q1",
			ValueType: "categorical", Aggregate: "first",
			Functions: []ExtractionFunctionConf{
				{Function: "select", Params: []byte(`{"path": "response"}`)},
			},
		},
	)

	actual, errs, err := Reduce(events, conf, NewAdAttributions())

	assert.Nil(t, err)
	assert.Contains(t, errorsByEntity(errs), entityAdUnmapped)
	assert.Equal(t, []byte(`"yes"`), []byte(actual["u1"].Data["q1"].Value))
	assert.NotContains(t, actual["u1"].Data, "gender")
}

func TestReduce_CrossStudyTokenMissesRatherThanImportingForeignStrata(t *testing.T) {
	// The mapping is loaded per study. A token belonging to another study is
	// simply absent, so it lands in `unmapped` — which is the correct, visible
	// behaviour. The alternative, a global mapping, would silently attribute
	// this respondent to another study's stratum.
	events := []*InferenceDataEvent{tokenEvent("u1", "other-studys-token", ti("07"))}

	attributions := loadedMapping(attribution("this-studys-token", "stratum-1",
		map[string]string{"gender": "women"}))

	actual, errs, err := Reduce(events, confWith(lookupConf("gender")), attributions)

	assert.Nil(t, err)
	assert.Empty(t, actual)
	assert.Contains(t, errorsByEntity(errs), entityAdUnmapped)
}

func TestReduce_KeyMissingFromAFoundRowIsNotUnmapped(t *testing.T) {
	// The row exists, so the respondent is mapped; the conf just asks for a
	// stratum variable the ad was not frozen with. That is a conf problem, not a
	// mapping problem, and must not inflate the unmapped counter that exists to
	// catch real bugs.
	events := []*InferenceDataEvent{tokenEvent("u1", "tok", ti("07"))}

	attributions := loadedMapping(attribution("tok", "stratum-1", map[string]string{"gender": "women"}))

	actual, errs, err := Reduce(events, confWith(lookupConf("nonexistent")), attributions)

	assert.Nil(t, err)
	assert.Empty(t, actual)
	assert.Len(t, errs, 0)
}

func TestClassifyExtractionError_LeavesOtherEntitiesAsTheyWere(t *testing.T) {
	// Regression guard on the routing: unmapped *sources* stay warnings and
	// everything else stays an extraction_error at warning severity, which is
	// what it was before ad attribution existed.
	eventType, severity := classifyExtractionError("source=Fly HPV Double")
	assert.Equal(t, eventExtractionWarning, eventType)
	assert.Equal(t, severityWarning, severity)

	eventType, severity = classifyExtractionError("var=md:gender")
	assert.Equal(t, eventExtractionError, eventType)
	assert.Equal(t, severityWarning, severity)
}

// --------------------------------------------------------------------------
// GetAdAttributions — the shell
// --------------------------------------------------------------------------

const insertAttribution = `
INSERT INTO ad_attributions(network, ad_id, study_id, stratum_id, creative_name, shortcode, metadata, resolved_from, ref_token)
VALUES($1, $2, $3, $4, $5, $6, $7, $8, $9)`

func insertAdAttribution(t *testing.T, pool *pgxpool.Pool, study, adID, stratum, md, refToken string) {
	t.Helper()

	// NULL, not "", is what a destination that is not in ref_mode "encoded"
	// writes — and it is the normal case, so the loader has to handle it.
	var token *string
	if refToken != "" {
		token = &refToken
	}

	MustExec(t, pool, insertAttribution,
		NetworkFacebook, adID, study, stratum, "Smiling", "mnchweek", md, "ad_id", token)
}

func TestGetAdAttributions_LoadsOnlyTheRequestedStudy(t *testing.T) {
	pool := TestPool()
	defer pool.Close()
	resetDb(pool)

	mine := CreateStudy(pool, "mine")
	theirs := CreateStudy(pool, "theirs")

	insertAdAttribution(t, pool, mine, "ad-1", "stratum-1", `{"gender": "women"}`, "tok-mine")
	insertAdAttribution(t, pool, theirs, "ad-2", "stratum-9", `{"gender": "men"}`, "tok-theirs")

	attributions, err := GetAdAttributions(pool, mine)

	assert.Nil(t, err)
	assert.Equal(t, 1, attributions.Len())
	assert.Equal(t, "stratum-1", attributions.ByRefToken["tok-mine"].Stratum)
	assert.Equal(t, NetworkFacebook, attributions.ByRefToken["tok-mine"].Network)
	assert.Equal(t, "ad-1", attributions.ByRefToken["tok-mine"].AdID,
		"ad_id is still captured on the row, it is just never joined on")
	assert.Equal(t, []byte(`"women"`), []byte(attributions.ByRefToken["tok-mine"].Metadata["gender"]))
	assert.NotContains(t, attributions.ByRefToken, "tok-theirs")
}

func TestGetAdAttributions_SkipsRowsWithNoToken(t *testing.T) {
	// A NULL ref_token is the normal case for a destination that is not in
	// ref_mode "encoded". The row loads without error and is simply not indexed
	// — there is no join key to index it under. Critically it must not land
	// under "", where every tokenless respondent would match it.
	pool := TestPool()
	defer pool.Close()
	resetDb(pool)

	study := CreateStudy(pool, "mixed")
	insertAdAttribution(t, pool, study, "ad-legacy", "stratum-1", `{"gender": "women"}`, "")
	insertAdAttribution(t, pool, study, "ad-encoded", "stratum-2", `{"gender": "men"}`, "tok")

	attributions, err := GetAdAttributions(pool, study)

	assert.Nil(t, err)
	assert.Equal(t, 1, attributions.Len(), "only the row with a token is joinable")
	assert.NotContains(t, attributions.ByRefToken, "")
	assert.Equal(t, "stratum-2", attributions.ByRefToken["tok"].Stratum)
}

func TestGetAdAttributions_IsEmptyRatherThanNilForAStudyWithNoAds(t *testing.T) {
	pool := TestPool()
	defer pool.Close()
	resetDb(pool)

	study := CreateStudy(pool, "empty")

	attributions, err := GetAdAttributions(pool, study)

	assert.Nil(t, err)
	assert.Equal(t, 0, attributions.Len())
	assert.NotNil(t, attributions.ByRefToken)
}

// --------------------------------------------------------------------------
// End to end, through swooshStudy
// --------------------------------------------------------------------------

const adInfConf = `
{
   "data_sources": {
       "fly": {
           "extraction_confs": [{
                  "location": "metadata",
                  "mapping": "ad_table_lookup",
                  "key": "vt",
                  "name": "gender",
                  "functions": [{"function": "select", "params": { "path": "" }}],
                  "value_type": "categorical",
                  "aggregate": "first"
              }]
        }
   }
}
`

func insertTokenEvent(t *testing.T, pool *pgxpool.Pool, study, token string) {
	t.Helper()
	e := &InferenceDataEvent{
		User: User{
			ID:       "test-user",
			Metadata: map[string]json.RawMessage{tokenKey: json.RawMessage(fmt.Sprintf("%q", token))},
		},
		Study:      study,
		SourceConf: &SourceConf{Name: "fly"},
		Timestamp:  time.Now().UTC(),
		Variable:   "q1",
		Value:      json.RawMessage(`{"value": "yes"}`),
		AdID:       "ad-" + token,
		AdNetwork:  NetworkFacebook,
	}
	b, err := json.Marshal(e)
	if err != nil {
		t.Fatal(err)
	}
	MustExec(t, pool, insertEventSQL, study, "fly", e.Timestamp, b, 0, "")
}

func countUnmappedEvents(t *testing.T, pool *pgxpool.Pool, study string) int {
	t.Helper()
	var n int
	err := pool.QueryRow(context.Background(),
		`SELECT COUNT(*) FROM study_run_events
		 WHERE study_id = $1 AND fingerprint = $2 AND event_type = $3`,
		study, fingerprintExPrefix+entityAdUnmapped, eventExtractionError).Scan(&n)
	if err != nil {
		t.Fatal(err)
	}
	return n
}

// TestSwooshStudy_UnmappedTokenIsSelfHealing is the property that makes the
// unmapped counter safe to alert on.
//
// swoosh recomputes a study's whole history on every run, so inserting a
// missing mapping row retroactively fixes every prior run's attribution. The
// counter is a current-state measure, not a cumulative one: the run after the
// fix emits no unmapped error at all, and the dashboard's 90-minute recency
// window then ages the old one out without anyone closing it.
func TestSwooshStudy_UnmappedTokenIsSelfHealing(t *testing.T) {
	pool := TestPool()
	defer pool.Close()
	resetDb(pool)

	study := CreateStudy(pool, "healing")
	MustExec(t, pool, insertConf, study, "inference_data", adInfConf)
	insertTokenEvent(t, pool, study, "tok-1")

	// Run 1: the ad exists but its mapping row does not.
	assert.Nil(t, swooshStudy(pool, study))
	assert.Equal(t, 1, countUnmappedEvents(t, pool, study),
		"a missing mapping row must be reported, loudly")

	var attributed int
	err := pool.QueryRow(context.Background(),
		`SELECT COUNT(*) FROM inference_data WHERE study_id = $1`, study).Scan(&attributed)
	assert.Nil(t, err)
	assert.Equal(t, 0, attributed, "nothing can be attributed without the row")

	// The fix: the row lands (in production, from a re-run of adopt).
	insertAdAttribution(t, pool, study, "ad-1", "stratum-1", `{"gender": "women"}`, "tok-1")

	// Run 2: same events, no code change, no backfill.
	assert.Nil(t, swooshStudy(pool, study))
	assert.Equal(t, 1, countUnmappedEvents(t, pool, study),
		"run 2 must emit no NEW unmapped error; the run-1 fact stays in the log and ages out")

	var value string
	err = pool.QueryRow(context.Background(),
		`SELECT value::string FROM inference_data WHERE study_id = $1 AND variable = 'gender'`,
		study).Scan(&value)
	assert.Nil(t, err)
	assert.Equal(t, `"women"`, value, "history is re-attributed retroactively")
}

func TestSwooshStudy_AttributesThroughTheMapping(t *testing.T) {
	pool := TestPool()
	defer pool.Close()
	resetDb(pool)

	study := CreateStudy(pool, "attributed")
	MustExec(t, pool, insertConf, study, "inference_data", adInfConf)
	insertAdAttribution(t, pool, study, "ad-1", "stratum-1", `{"gender": "women"}`, "tok-1")
	insertTokenEvent(t, pool, study, "tok-1")

	assert.Nil(t, swooshStudy(pool, study))

	assert.Equal(t, 0, countUnmappedEvents(t, pool, study))

	var value string
	err := pool.QueryRow(context.Background(),
		`SELECT value::string FROM inference_data WHERE study_id = $1 AND variable = 'gender'`,
		study).Scan(&value)
	assert.Nil(t, err)
	assert.Equal(t, `"women"`, value)
}

func TestSwooshStudy_MappingRowOutlivesItsAd(t *testing.T) {
	// ad_attributions has no FK to studies and is never derived from live
	// Facebook state, so a row for an ad reconciliation has since deleted is
	// still there to attribute a respondent who arrived from a reshared post.
	// Nothing in swoosh may filter on ad liveness.
	pool := TestPool()
	defer pool.Close()
	resetDb(pool)

	study := CreateStudy(pool, "deleted-ad")
	MustExec(t, pool, insertConf, study, "inference_data", adInfConf)
	insertAdAttribution(t, pool, study, "long-deleted-ad", "stratum-1", `{"gender": "women"}`, "tok-1")
	insertTokenEvent(t, pool, study, "tok-1")

	assert.Nil(t, swooshStudy(pool, study))

	var value string
	err := pool.QueryRow(context.Background(),
		`SELECT value::string FROM inference_data WHERE study_id = $1 AND variable = 'gender'`,
		study).Scan(&value)
	assert.Nil(t, err)
	assert.Equal(t, `"women"`, value)
}
