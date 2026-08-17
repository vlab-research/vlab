package main

// Ad-ID attribution in swoosh (A6 + A7).
//
// vlab owns the ad -> stratum join. `location: "ad"` resolves a variable through
// the frozen ad_attributions row for the ad that recruited the respondent,
// instead of through the dotted ref smuggled into the event's metadata.
//
// The failure mode this guards against is quiet: a retrieve returning ok=false
// means `continue` — no variable, no stratum match, optimizer undercount. It
// does not error, it miscounts. So the tests below care as much about *which
// counter* an event lands in as about the value it produces.

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

func adEvent(user, adID string, ts time.Time) *InferenceDataEvent {
	return &InferenceDataEvent{
		User:       User{ID: user},
		SourceConf: &SourceConf{Name: "fly"},
		Timestamp:  ts,
		Variable:   "q1",
		Value:      json.RawMessage(`{"response": "yes"}`),
		AdID:       adID,
		AdNetwork:  NetworkFacebook,
	}
}

// organicEvent has no ad id, which is what an entrant who never clicked an ad
// looks like: someone who was given the shortcode directly, or arrived via a
// reshared page post.
func organicEvent(user string, ts time.Time) *InferenceDataEvent {
	e := adEvent(user, "", ts)
	e.AdNetwork = ""
	return e
}

// adConf declares one ad-derived variable. Note that the user supplies name,
// value_type and aggregate exactly as for any other location — vlab derives
// nothing here.
func adConf(key, name string) *ExtractionConf {
	return &ExtractionConf{
		Location:  "ad",
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

func attribution(adID, stratum string, md map[string]string) AdAttribution {
	raw := map[string]json.RawMessage{}
	for k, v := range md {
		b, err := json.Marshal(v)
		if err != nil {
			panic(err)
		}
		raw[k] = b
	}
	return AdAttribution{
		AdID:     adID,
		Network:  NetworkFacebook,
		Stratum:  stratum,
		Metadata: raw,
	}
}

func errorsByEntity(errs []ExtractionError) map[string]ExtractionError {
	m := map[string]ExtractionError{}
	for _, e := range errs {
		m[e.Entity] = e
	}
	return m
}

// --------------------------------------------------------------------------
// A6: the "ad" extraction location
// --------------------------------------------------------------------------

func TestReduce_AdLocationResolvesThroughTheFrozenMapping(t *testing.T) {
	// The whole point: the variable comes out with the name the *user*
	// declared, and the value the ad was frozen with — not from anything the
	// respondent said and not from the event's metadata.
	events := []*InferenceDataEvent{adEvent("u1", "ad-1", ti("07"))}

	attributions := AdAttributions{
		"ad-1": attribution("ad-1", "stratum-1", map[string]string{
			"creative": "Smiling",
			"gender":   "women",
			"form":     "mnchweek",
		}),
	}

	actual, errs, err := Reduce(events, confWith(adConf("gender", "md:gender")), attributions)

	assert.Nil(t, err)
	assert.Len(t, errs, 0)
	assert.Equal(t, InferenceData{
		"u1": {User: "u1", Data: map[string]*InferenceDataValue{
			"md:gender": {
				Timestamp: ti("07"),
				Variable:  "md:gender",
				Value:     []byte(`"women"`),
				ValueType: "categorical",
			},
		}},
	}, actual)
}

func TestReduce_AdLocationResolvesCreativeAndFormKeys(t *testing.T) {
	// `creative` and `form` are the two keys that only exist because the frozen
	// blob is the ref's dict rather than stratum.metadata (see the A2 invariant
	// in adopt/adopt/test_marketing.py). If the mapping were built from the
	// stratum conf, these two would resolve to nothing.
	events := []*InferenceDataEvent{adEvent("u1", "ad-1", ti("07"))}

	attributions := AdAttributions{
		"ad-1": attribution("ad-1", "stratum-1", map[string]string{
			"creative": "Smiling",
			"form":     "mnchweek",
		}),
	}

	actual, errs, err := Reduce(
		events,
		confWith(adConf("creative", "md:creative"), adConf("form", "md:form")),
		attributions,
	)

	assert.Nil(t, err)
	assert.Len(t, errs, 0)
	assert.Equal(t, []byte(`"Smiling"`), []byte(actual["u1"].Data["md:creative"].Value))
	assert.Equal(t, []byte(`"mnchweek"`), []byte(actual["u1"].Data["md:form"].Value))
}

func TestReduce_AdLocationDoesNotFallBackToMetadata(t *testing.T) {
	// There is deliberately no fallback. `location: "ad"` is for new studies
	// only; a fallback would let someone swap an existing study's conf and
	// silently re-attribute its whole back-catalogue through a path its events
	// cannot satisfy, because swoosh recomputes all history every run.
	//
	// Here the event carries the answer in metadata and the mapping does not
	// have the ad. Nothing must come out.
	e := adEvent("u1", "ad-missing", ti("07"))
	e.User.Metadata = map[string]json.RawMessage{"gender": []byte(`"women"`)}

	actual, errs, err := Reduce(
		[]*InferenceDataEvent{e},
		confWith(adConf("gender", "md:gender")),
		AdAttributions{},
	)

	assert.Nil(t, err)
	assert.Empty(t, actual, "metadata must not be consulted for an ad-location conf")

	// ...and it is reported as unmapped rather than passing silently.
	assert.Contains(t, errorsByEntity(errs), entityAdUnmapped)
}

func TestReduce_MetadataLocationIsUnaffectedByAttributions(t *testing.T) {
	// Existing studies keep `location: "metadata"` forever and must be
	// completely untouched by any of this.
	e := adEvent("u1", "", ti("07"))
	e.User.Metadata = map[string]json.RawMessage{"gender": []byte(`"women"`)}

	conf := &ExtractionConf{
		Location: "metadata", Key: "gender", Name: "md:gender",
		ValueType: "categorical", Aggregate: "first",
		Functions: []ExtractionFunctionConf{
			{Function: "select", Params: []byte(`{"path": ""}`)},
		},
	}

	actual, errs, err := Reduce([]*InferenceDataEvent{e}, confWith(conf), nil)

	assert.Nil(t, err)
	assert.Len(t, errs, 0, "a metadata-only study must produce no ad outcomes at all")
	assert.Equal(t, []byte(`"women"`), []byte(actual["u1"].Data["md:gender"].Value))
}

func TestReduce_TakesTheMappingAsDataSoLookupsCostNothingPerEvent(t *testing.T) {
	// Reduce has no *pgxpool.Pool in its signature and retrieveFromAd closes
	// over a plain map, so a per-event database call is not merely avoided, it
	// is unrepresentable. The mapping is loaded exactly once per study, in
	// swooshStudy, and passed down. If anyone moves the load into the
	// RetrieveFunc — which runs once per event per conf — this test stops
	// compiling, which is the point.
	events := []*InferenceDataEvent{}
	for i := 0; i < 1000; i++ {
		events = append(events, adEvent(fmt.Sprintf("u%d", i), "ad-1", ti("07")))
	}

	attributions := AdAttributions{
		"ad-1": attribution("ad-1", "stratum-1", map[string]string{"gender": "women"}),
	}

	actual, errs, err := Reduce(events, confWith(adConf("gender", "md:gender")), attributions)

	assert.Nil(t, err)
	assert.Len(t, errs, 0)
	assert.Len(t, actual, 1000)
}

// --------------------------------------------------------------------------
// A7: the three-way split
// --------------------------------------------------------------------------

func TestReduce_AttributedProducesNoOutcomeEvent(t *testing.T) {
	events := []*InferenceDataEvent{adEvent("u1", "ad-1", ti("07"))}
	attributions := AdAttributions{
		"ad-1": attribution("ad-1", "stratum-1", map[string]string{"gender": "women"}),
	}

	_, errs, err := Reduce(events, confWith(adConf("gender", "md:gender")), attributions)

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

	_, errs, err := Reduce(events, confWith(adConf("gender", "md:gender")), AdAttributions{})

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

func TestReduce_UnmappedAdIsACountedError(t *testing.T) {
	// Always a bug: vlab created an ad and failed to record what it meant.
	// Every respondent it recruits is dropped from stratum counts.
	events := []*InferenceDataEvent{
		adEvent("u1", "ad-unknown", ti("07")),
		adEvent("u2", "ad-unknown", ti("08")),
		adEvent("u3", "ad-other-unknown", ti("09")),
	}

	_, errs, err := Reduce(events, confWith(adConf("gender", "md:gender")), AdAttributions{})

	assert.Nil(t, err)
	byEntity := errorsByEntity(errs)

	unmapped, ok := byEntity[entityAdUnmapped]
	assert.True(t, ok, "an ad id with no mapping row must be reported")
	assert.Equal(t, 3, unmapped.Count, "aggregated per entity, one error with a count")
	assert.NotContains(t, byEntity, entityAdOrganic, "an ad id present is not organic")

	// This is the one outcome that alarms.
	eventType, severity := classifyExtractionError(entityAdUnmapped)
	assert.Equal(t, eventExtractionError, eventType)
	assert.Equal(t, severityError, severity)
}

func TestReduce_SplitsAllThreeWaysInOneRun(t *testing.T) {
	events := []*InferenceDataEvent{
		adEvent("attributed", "ad-1", ti("07")),
		organicEvent("organic", ti("08")),
		adEvent("unmapped", "ad-nope", ti("09")),
	}

	attributions := AdAttributions{
		"ad-1": attribution("ad-1", "stratum-1", map[string]string{"gender": "women"}),
	}

	actual, errs, err := Reduce(events, confWith(adConf("gender", "md:gender")), attributions)

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
	// Classification is a property of the event — it either carries an ad id or
	// it does not. Counting per conf would multiply one organic arrival by the
	// number of ad-location confs the study happens to declare, which would
	// make the counter meaningless.
	events := []*InferenceDataEvent{organicEvent("u1", ti("07"))}

	conf := confWith(
		adConf("gender", "md:gender"),
		adConf("Age", "md:age"),
		adConf("creative", "md:creative"),
	)

	_, errs, err := Reduce(events, conf, AdAttributions{})

	assert.Nil(t, err)
	assert.Equal(t, 1, errorsByEntity(errs)[entityAdOrganic].Count,
		"one event, three ad confs, one organic count")
}

func TestReduce_NoAdConfsMeansNoAdOutcomesEvenWithoutAdIds(t *testing.T) {
	// The guard that keeps every existing study silent. A study on the old path
	// has no ad-location confs, so its events — which carry no ad_id — must not
	// produce a flood of "organic" counts.
	e := organicEvent("u1", ti("07"))
	e.User.Metadata = map[string]json.RawMessage{"gender": []byte(`"women"`)}

	conf := confWith(&ExtractionConf{
		Location: "metadata", Key: "gender", Name: "md:gender",
		ValueType: "categorical", Aggregate: "first",
		Functions: []ExtractionFunctionConf{
			{Function: "select", Params: []byte(`{"path": ""}`)},
		},
	})

	_, errs, err := Reduce([]*InferenceDataEvent{e}, conf, AdAttributions{})

	assert.Nil(t, err)
	assert.Len(t, errs, 0)
}

func TestReduce_UnmappedAdStillYieldsItsSurveyAnswers(t *testing.T) {
	// A missing mapping row must not also cost us the respondent's answers.
	// The ad-derived variable is lost (and counted); the `variable` conf is not.
	events := []*InferenceDataEvent{adEvent("u1", "ad-nope", ti("07"))}

	conf := confWith(
		adConf("gender", "md:gender"),
		&ExtractionConf{
			Location: "variable", Key: "q1", Name: "q1",
			ValueType: "categorical", Aggregate: "first",
			Functions: []ExtractionFunctionConf{
				{Function: "select", Params: []byte(`{"path": "response"}`)},
			},
		},
	)

	actual, errs, err := Reduce(events, conf, AdAttributions{})

	assert.Nil(t, err)
	assert.Contains(t, errorsByEntity(errs), entityAdUnmapped)
	assert.Equal(t, []byte(`"yes"`), []byte(actual["u1"].Data["q1"].Value))
	assert.NotContains(t, actual["u1"].Data, "md:gender")
}

func TestReduce_CrossStudyAdIdMissesRatherThanImportingForeignStrata(t *testing.T) {
	// The mapping is loaded per study. An ad id belonging to another study is
	// simply absent, so it lands in `unmapped` — which is the correct, visible
	// behaviour. The alternative, a global mapping, would silently attribute
	// this respondent to another study's stratum.
	events := []*InferenceDataEvent{adEvent("u1", "other-studys-ad", ti("07"))}

	attributions := AdAttributions{
		"this-studys-ad": attribution("this-studys-ad", "stratum-1",
			map[string]string{"gender": "women"}),
	}

	actual, errs, err := Reduce(events, confWith(adConf("gender", "md:gender")), attributions)

	assert.Nil(t, err)
	assert.Empty(t, actual)
	assert.Contains(t, errorsByEntity(errs), entityAdUnmapped)
}

func TestReduce_KeyMissingFromAFoundRowIsNotUnmapped(t *testing.T) {
	// The row exists, so the ad is mapped; the conf just asks for a key the ad
	// was not frozen with. That is a conf problem, not a mapping problem, and
	// must not inflate the unmapped counter that exists to catch real bugs.
	events := []*InferenceDataEvent{adEvent("u1", "ad-1", ti("07"))}

	attributions := AdAttributions{
		"ad-1": attribution("ad-1", "stratum-1", map[string]string{"gender": "women"}),
	}

	actual, errs, err := Reduce(events, confWith(adConf("nonexistent", "md:nope")), attributions)

	assert.Nil(t, err)
	assert.Empty(t, actual)
	assert.Len(t, errs, 0)
}

func TestClassifyExtractionError_LeavesOtherEntitiesAsTheyWere(t *testing.T) {
	// Regression guard on the routing change: unmapped *sources* stay warnings
	// and everything else stays an extraction_error at warning severity, which
	// is what it was before ad attribution existed.
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
INSERT INTO ad_attributions(network, ad_id, study_id, stratum_id, creative_name, shortcode, metadata, resolved_from)
VALUES($1, $2, $3, $4, $5, $6, $7, $8)`

func insertAdAttribution(t *testing.T, pool *pgxpool.Pool, study, adID, stratum, md string) {
	t.Helper()
	MustExec(t, pool, insertAttribution,
		NetworkFacebook, adID, study, stratum, "Smiling", "mnchweek", md, "ad_id")
}

func TestGetAdAttributions_LoadsOnlyTheRequestedStudy(t *testing.T) {
	pool := TestPool()
	defer pool.Close()
	resetDb(pool)

	mine := CreateStudy(pool, "mine")
	theirs := CreateStudy(pool, "theirs")

	insertAdAttribution(t, pool, mine, "ad-1", "stratum-1", `{"gender": "women"}`)
	insertAdAttribution(t, pool, theirs, "ad-2", "stratum-9", `{"gender": "men"}`)

	attributions, err := GetAdAttributions(pool, mine)

	assert.Nil(t, err)
	assert.Len(t, attributions, 1)
	assert.Equal(t, "stratum-1", attributions["ad-1"].Stratum)
	assert.Equal(t, NetworkFacebook, attributions["ad-1"].Network)
	assert.Equal(t, []byte(`"women"`), []byte(attributions["ad-1"].Metadata["gender"]))
	assert.NotContains(t, attributions, "ad-2")
}

func TestGetAdAttributions_IsEmptyRatherThanNilForAStudyWithNoAds(t *testing.T) {
	pool := TestPool()
	defer pool.Close()
	resetDb(pool)

	study := CreateStudy(pool, "empty")

	attributions, err := GetAdAttributions(pool, study)

	assert.Nil(t, err)
	assert.Len(t, attributions, 0)
}

// --------------------------------------------------------------------------
// End to end, through swooshStudy
// --------------------------------------------------------------------------

const adInfConf = `
{
   "data_sources": {
       "fly": {
           "extraction_confs": [{
                  "location": "ad",
                  "key": "gender",
                  "name": "md:gender",
                  "functions": [{"function": "select", "params": { "path": "" }}],
                  "value_type": "categorical",
                  "aggregate": "first"
              }]
        }
   }
}
`

func insertAdEvent(t *testing.T, pool *pgxpool.Pool, study, adID string) {
	t.Helper()
	e := &InferenceDataEvent{
		User:       User{ID: "test-user"},
		Study:      study,
		SourceConf: &SourceConf{Name: "fly"},
		Timestamp:  time.Now().UTC(),
		Variable:   "q1",
		Value:      json.RawMessage(`{"value": "yes"}`),
		AdID:       adID,
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

// TestSwooshStudy_UnmappedAdIsSelfHealing is the property that makes the
// unmapped counter safe to alert on.
//
// swoosh recomputes a study's whole history on every run, so inserting a
// missing mapping row retroactively fixes every prior run's attribution. The
// counter is a current-state measure, not a cumulative one: the run after the
// fix emits no unmapped error at all, and the dashboard's 90-minute recency
// window then ages the old one out without anyone closing it.
func TestSwooshStudy_UnmappedAdIsSelfHealing(t *testing.T) {
	pool := TestPool()
	defer pool.Close()
	resetDb(pool)

	study := CreateStudy(pool, "healing")
	MustExec(t, pool, insertConf, study, "inference_data", adInfConf)
	insertAdEvent(t, pool, study, "ad-1")

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
	insertAdAttribution(t, pool, study, "ad-1", "stratum-1", `{"gender": "women"}`)

	// Run 2: same events, no code change, no backfill.
	assert.Nil(t, swooshStudy(pool, study))
	assert.Equal(t, 1, countUnmappedEvents(t, pool, study),
		"run 2 must emit no NEW unmapped error; the run-1 fact stays in the log and ages out")

	var value string
	err = pool.QueryRow(context.Background(),
		`SELECT value::string FROM inference_data WHERE study_id = $1 AND variable = 'md:gender'`,
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
	insertAdAttribution(t, pool, study, "ad-1", "stratum-1", `{"gender": "women"}`)
	insertAdEvent(t, pool, study, "ad-1")

	assert.Nil(t, swooshStudy(pool, study))

	assert.Equal(t, 0, countUnmappedEvents(t, pool, study))

	var value string
	err := pool.QueryRow(context.Background(),
		`SELECT value::string FROM inference_data WHERE study_id = $1 AND variable = 'md:gender'`,
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
	insertAdAttribution(t, pool, study, "long-deleted-ad", "stratum-1", `{"gender": "women"}`)
	insertAdEvent(t, pool, study, "long-deleted-ad")

	assert.Nil(t, swooshStudy(pool, study))

	var value string
	err := pool.QueryRow(context.Background(),
		`SELECT value::string FROM inference_data WHERE study_id = $1 AND variable = 'md:gender'`,
		study).Scan(&value)
	assert.Nil(t, err)
	assert.Equal(t, `"women"`, value)
}
