package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"

	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	. "github.com/vlab-research/vlab/inference/inference-data"
	. "github.com/vlab-research/vlab/inference/test-helpers"
)

func check(e error) {
	if e != nil {
		panic(e)
	}
}

func resData(fi string) string {
	b, e := ioutil.ReadFile(fmt.Sprintf("test/%s", fi))
	check(e)

	return string(b)
}

func dataAssertions(t *testing.T, e []*InferenceDataEvent) {
	assert.Equal(t, 8, len(e))

	assert.Equal(t, "126", e[0].User.ID)
	assert.Equal(t, "129", e[3].User.ID)
	assert.Equal(t, "133", e[7].User.ID)

	assert.Equal(t, "ref", e[0].Variable)
	assert.Equal(t, "phone_number", e[3].Variable)
	assert.Equal(t, "my_custom_dropdown_reference", e[7].Variable)

	timestamp := time.Time(time.Date(2022, time.July, 21, 22, 33, 56, 0, time.UTC))
	assert.Equal(t, timestamp, e[0].Timestamp)

	timestamp = time.Time(time.Date(2017, time.September, 14, 22, 33, 56, 0, time.UTC))
	assert.Equal(t, timestamp, e[3].Timestamp)

	ans := `{"response":"last","translated_response":"último","survey_id":"be5ae9dd-0189-478e-8a3d-4d8ead8240a4","shortcode":"101"}`
	assert.Equal(t, ans, string(e[0].Value))
	ans = `{"response":"first","translated_response":"primero","survey_id":"pgixf9jqwz3z2x2xy5tqw92d5dyz44nc","shortcode":"108"}`
	ans = `{"response":"hello","translated_response":"hola","survey_id":"pgixf9jqwz3z2x2xy5tqw92d5dyz44nc","shortcode":"108"}`
	assert.Equal(t, ans, string(e[7].Value))
}

func TestGetResponses_PaginatesUntilEmpty(t *testing.T) {
	res1 := resData("fly_example.json")
	res2 := resData("fly_example2.json")

	s := string(res1)
	data := GetResponsesResponse{}
	json.Unmarshal([]byte(s), &data)

	s2 := string(res2)
	data2 := GetResponsesResponse{}
	json.Unmarshal([]byte(s2), &data2)

	count := 0
	ts, _ := TestServer(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "/responses", r.URL.Path)

		// Assert auth header
		auth := r.Header.Get("Authorization")
		assert.Equal(t, "Bearer sosecret", auth)

		surveyName := r.URL.Query().Get("survey")
		assert.Equal(t, "foo survey", surveyName)

		// Check token is paginating properly
		after := r.URL.Query().Get("after")

		if count == 0 {
			assert.NotEqual(t, "", after, "No token sent")
			assert.Equal(t, "oldtoken", after)

			w.WriteHeader(http.StatusOK)
			w.Header().Set("Content-Type", "application/json")
			fmt.Fprint(w, res1)
		}

		if count == 1 {
			assert.Equal(t, "4viu4r8djwxwb2udbivx42avnawwj5wj", after)
			w.WriteHeader(http.StatusOK)
			w.Header().Set("Content-Type", "application/json")
			fmt.Fprint(w, res2)
		}

		if count == 2 {
			assert.Equal(t, "3btcnj9rrhzyttmghhapu6znz3y43i36", after)
			w.WriteHeader(http.StatusOK)
			w.Header().Set("Content-Type", "application/json")
			fmt.Fprint(w, `{"responses": []}`)
		}

		count++

	})

	tc := FlyConnector{BaseUrl: ts.URL, PageSize: 4}

	cnf := &SourceConf{
		Name:   "",
		Source: "",
		Config: []byte(`{"survey_name": "foo survey"}`),
	}

	source := &Source{
		StudyID: "mystudy",
		Conf:    cnf,
		Credentials: &Credentials{
			Entity:  "fly",
			Key:     "default",
			Details: []byte(`{"api_key": "sosecret"}`),
			Created: time.Now().UTC(),
		},
	}

	events := tc.GetResponses(source, "oldtoken", 0)

	e := Sliceit(events)
	dataAssertions(t, e)

	assert.Equal(t, 3, count)
}

func TestGetResponses_PaginatesUntilLastPartialPage(t *testing.T) {
	res1 := resData("fly_example.json")
	res2 := resData("fly_example2.json")

	s := string(res1)
	data := GetResponsesResponse{}
	json.Unmarshal([]byte(s), &data)

	s2 := string(res2)
	data2 := GetResponsesResponse{}
	json.Unmarshal([]byte(s2), &data2)

	count := 0
	ts, _ := TestServer(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "/responses", r.URL.Path)

		w.WriteHeader(http.StatusOK)
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprint(w, res1)
		count++
	})

	tc := FlyConnector{BaseUrl: ts.URL, PageSize: 6}

	cnf := &SourceConf{
		Name:   "",
		Source: "",
		Config: []byte(`{"survey_name": "foo survey"}`),
	}

	source := &Source{
		StudyID: "mystudy",
		Conf:    cnf,
		Credentials: &Credentials{
			Entity:  "fly",
			Key:     "default",
			Details: []byte(`{"api_key": "sosecret"}`),
			Created: time.Now().UTC(),
		},
	}

	events := tc.GetResponses(source, "oldtoken", 0)
	e := Sliceit(events)
	assert.Equal(t, 4, len(e))

	assert.Equal(t, 1, count)
}

// -----------------------------------------------------------------------
// A5: ad-ID attribution.
//
// Fly now surfaces a first-class `ad_id` on each response, resolved by fly
// itself from the Messenger/WhatsApp referral. These tests cover mapping
// that ad id to an (ad_id, ad_network) pair on the emitted InferenceDataEvent,
// and that the mapping degrades safely (empty string, never a guess) when
// fly's platform or ad id is missing or unrecognised.
// -----------------------------------------------------------------------

func TestAdNetworkForPlatform_MapsMessagingPlatformsToFacebookAdNetwork(t *testing.T) {
	// This is the single most important assertion in the file. The return
	// value here is the *ad* network, not the messaging channel: a Messenger
	// ad and a WhatsApp ad are both bought and served through Meta's ad
	// system, so their ad ids live in the same namespace. ad_attributions is
	// keyed (network, ad_id) — if this returned "whatsapp" instead of
	// "facebook", every WhatsApp-sourced ad id would fail to match a row in
	// ad_attributions. That failure is silent: no error, just a respondent
	// who never gets attributed to a stratum.
	assert.Equal(t, NetworkFacebook, adNetworkForPlatform("messenger"))
	assert.Equal(t, NetworkFacebook, adNetworkForPlatform("whatsapp"))
	assert.Equal(t, "facebook", adNetworkForPlatform("whatsapp"))
}

func TestAdNetworkForPlatform_UnrecognisedOrEmptyPlatformYieldsEmptyString(t *testing.T) {
	// An unmapped platform must come back as "", not a guessed network.
	assert.Equal(t, "", adNetworkForPlatform(""))
	assert.Equal(t, "", adNetworkForPlatform("instagram"))
	assert.Equal(t, "", adNetworkForPlatform("some-made-up-platform"))
}

func TestPlatformFromMetadata(t *testing.T) {
	md := map[string]json.RawMessage{
		"platform": json.RawMessage(`"whatsapp"`),
	}
	assert.Equal(t, "whatsapp", platformFromMetadata(md))

	// Key absent entirely.
	assert.Equal(t, "", platformFromMetadata(map[string]json.RawMessage{}))

	// Value present but not a JSON string.
	assert.Equal(t, "", platformFromMetadata(map[string]json.RawMessage{
		"platform": json.RawMessage(`123`),
	}))
	assert.Equal(t, "", platformFromMetadata(map[string]json.RawMessage{
		"platform": json.RawMessage(`{}`),
	}))
}

func TestAdFields_NoAdIDYieldsEmptyNetworkToo(t *testing.T) {
	// An organic respondent has no ad, so there is no network for an ad that
	// does not exist — even when the metadata happens to say "messenger".
	md := map[string]json.RawMessage{
		"platform": json.RawMessage(`"messenger"`),
	}
	adID, adNetwork := adFields("", md)
	assert.Equal(t, "", adID)
	assert.Equal(t, "", adNetwork)
}

func TestAdFields_RealAdIDPairsWithFacebookNetwork(t *testing.T) {
	mdMessenger := map[string]json.RawMessage{
		"platform": json.RawMessage(`"messenger"`),
	}
	adID, adNetwork := adFields("120254866237980150", mdMessenger)
	assert.Equal(t, "120254866237980150", adID)
	assert.Equal(t, "facebook", adNetwork)

	mdWhatsapp := map[string]json.RawMessage{
		"platform": json.RawMessage(`"whatsapp"`),
	}
	adID, adNetwork = adFields("120254866237980150", mdWhatsapp)
	assert.Equal(t, "120254866237980150", adID)
	assert.Equal(t, "facebook", adNetwork)
}

func TestAdFields_UnknownPlatformKeepsAdIDButEmptiesNetwork(t *testing.T) {
	// Deliberate, not a bug: swoosh looks up ad_attributions by ad id alone
	// (Meta ad ids are globally unique), so attribution still works even
	// without a network. The empty network is a visible signal that fly
	// grew a platform vlab has not mapped, rather than a silent mislabel.
	md := map[string]json.RawMessage{
		"platform": json.RawMessage(`"instagram"`),
	}
	adID, adNetwork := adFields("120254866237980150", md)
	assert.Equal(t, "120254866237980150", adID)
	assert.Equal(t, "", adNetwork)
}

func TestGetResponses_WiresAdIDAndAdNetworkFromFlyJSON(t *testing.T) {
	// End-to-end proof that the ad_id fly puts on the wire actually reaches
	// the emitted InferenceDataEvent, paired with the right ad network -
	// and that a response with no ad_id at all comes through with both
	// fields empty rather than erroring or zero-valuing something else.
	payload := `{
		"responses": [
			{
				"parent_surveyid": "be5ae9dd-0189-478e-8a3d-4d8ead8240a4",
				"parent_shortcode": "101",
				"shortcode": "101",
				"token": "adtoken1",
				"surveyid": "be5ae9dd-0189-478e-8a3d-4d8ead8240a4",
				"flowid": "100004",
				"userid": "200",
				"question_ref": "ref",
				"question_idx": "10",
				"question_text": "Job opportunities",
				"response": "last",
				"timestamp": "2022-07-21T22:33:56+00:00",
				"metadata": {"platform": "messenger"},
				"pageid": null,
				"translated_response": "last",
				"ad_id": "120254866237980150"
			},
			{
				"parent_surveyid": "c3c1d340-2335-492b-bb4f-6c0cccc2735f",
				"parent_shortcode": "102",
				"shortcode": "102",
				"token": "adtoken2",
				"surveyid": "c3c1d340-2335-492b-bb4f-6c0cccc2735f",
				"flowid": "100001",
				"userid": "201",
				"question_ref": "ref",
				"question_idx": "10",
				"question_text": "text",
				"response": "organic",
				"timestamp": "2021-07-20T02:44:15+00:00",
				"metadata": null,
				"pageid": null,
				"translated_response": "organic"
			}
		]
	}`

	ts, _ := TestServer(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprint(w, payload)
	})

	tc := FlyConnector{BaseUrl: ts.URL, PageSize: 4}

	cnf := &SourceConf{
		Name:   "",
		Source: "",
		Config: []byte(`{"survey_name": "foo survey"}`),
	}

	source := &Source{
		StudyID: "mystudy",
		Conf:    cnf,
		Credentials: &Credentials{
			Entity:  "fly",
			Key:     "default",
			Details: []byte(`{"api_key": "sosecret"}`),
			Created: time.Now().UTC(),
		},
	}

	events := tc.GetResponses(source, "", 0)
	e := Sliceit(events)
	assert.Equal(t, 2, len(e))

	assert.Equal(t, "120254866237980150", e[0].AdID)
	assert.Equal(t, "facebook", e[0].AdNetwork)

	assert.Equal(t, "", e[1].AdID)
	assert.Equal(t, "", e[1].AdNetwork)
}

func TestInferenceDataEvent_OmitsEmptyAdFieldsFromPersistedJSON(t *testing.T) {
	// inference_data_events stores the whole event as one JSON blob, so
	// `omitempty` on AdID/AdNetwork is what makes this change require no
	// migration and leaves every pre-existing event byte-identical: an
	// event with no ad never grows an "ad_id"/"ad_network" key at all.
	event := InferenceDataEvent{
		User:      User{ID: "1"},
		Study:     "mystudy",
		Variable:  "ref",
		AdID:      "",
		AdNetwork: "",
	}

	b, err := json.Marshal(event)
	assert.NoError(t, err)

	s := string(b)
	assert.NotContains(t, s, `"ad_id"`)
	assert.NotContains(t, s, `"ad_network"`)
}
