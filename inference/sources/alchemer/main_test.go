package main

import (
	"encoding/json"
	"fmt"
	"github.com/stretchr/testify/assert"

	. "github.com/vlab-research/vlab/inference/inference-data"
	. "github.com/vlab-research/vlab/inference/test-helpers"
	"io/ioutil"
	"net/http"
	"regexp"
	"strings"
	"testing"
	"time"
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

func normalizeSpace(s string) string {
	re := regexp.MustCompile(`\s+`)
	r := re.Split(s, -1)
	return strings.Join(r, " ")
}

func dataAssertions(t *testing.T, e []*InferenceDataEvent) {

	// Total number of responses and url variables
	assert.Equal(t, 67, len(e))

	// first element should have index of 1
	assert.Equal(t, 1, e[0].Idx)

	lookup := MakeUserMap(e)

	// first is URL variables, second is answered questions
	assert.Equal(t, 2, len(lookup["1"]))

	// Chck first user data looks good
	assert.Equal(t, `"CARMA0005"`, string(lookup["1"]["ticket"].Value))
	assert.Equal(t, "1", string(lookup["1"]["3"].User.ID))
	assert.Equal(t, `"Armenia"`, string(lookup["1"]["3"].User.Metadata["country"]))
	assert.Equal(t, `"0"`, GetString(lookup["1"]["3"].Value, "answer"))

	// Assert timestamp
	EDT, _ := time.LoadLocation("America/New_York")
	timestamp := time.Time(time.Date(2023, time.April, 10, 0, 57, 7, 0, EDT))
	assert.Equal(t, timestamp, lookup["1"]["3"].Timestamp)

	// Options is a bit funky, probably need to work on it.
	assert.Equal(t, `"1"`, GetString(lookup["4"]["11"].Value, "options.10101.answer"))
}

func TestGetResponses_WorksWithSinglePageFromExampleJson(t *testing.T) {
	res := resData("alchemer-response-1.json")
	empty := resData("alchemer-response-empty.json")
	count := 0
	ts, _ := TestServer(func(w http.ResponseWriter, r *http.Request) {

		if count == 0 {
			assert.Equal(t, "/v5/survey/135/surveyresponse", r.URL.Path)
			v := r.URL.Query()

			// Authentication goes in query params
			assert.Equal(t, "foo", v["api_token"][0])
			assert.Equal(t, "sosecret", v["api_token_secret"][0])

			// Filter to just complete
			assert.Equal(t, "status", v[`filter[field][0]`][0])
			assert.Equal(t, "Complete", v[`filter[value][0]`][0])

			w.WriteHeader(200)
			w.Header().Set("Content-Type", "application/json")
			fmt.Fprint(w, res)
		}

		if count == 1 {
			w.WriteHeader(200)
			w.Header().Set("Content-Type", "application/json")
			fmt.Fprint(w, empty)
		}

		count++
	})

	tc := AlchemerConnector{BaseUrl: ts.URL, PageSize: 5}

	cnf := &SourceConf{
		Name:   "",
		Source: "",
		Config: []byte(`{"survey_id": 135, "timezone": "America/New_York"}`),
	}

	config := new(AlchemerConfig)
	json.Unmarshal(cnf.Config, config)

	source := &Source{
		StudyID: "mystudy",
		Conf:    cnf,
		Credentials: &Credentials{
			Entity:  "alchemer",
			Key:     "key1",
			Details: []byte(`{"api_token": "foo", "api_token_secret": "sosecret"}`),
			Created: time.Now().UTC(),
		}}

	events := tc.GetResponses(source, config, "", 0)

	e := Sliceit(events)
	dataAssertions(t, e)

}

func TestGetResponses_PaginatesProperlyFromNothing(t *testing.T) {
	res1 := resData("alchemer-response-paginated-1.json")
	res2 := resData("alchemer-response-paginated-2.json")
	empty := resData("alchemer-response-empty.json")
	count := 0

	ts, _ := TestServer(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "/v5/survey/135/surveyresponse", r.URL.Path)
		v := r.URL.Query()

		if count == 0 {

			// Pagination doesn't exist on first call
			assert.Equal(t, []string([]string(nil)), v[`filter[field][1]`])

			w.WriteHeader(200)
			w.Header().Set("Content-Type", "application/json")
			fmt.Fprint(w, res1)
		}

		if count == 1 {

			// Pagination exists on the second call
			// with the proper token, last date_submitted
			assert.Equal(t, "date_submitted", v[`filter[field][1]`][0])
			assert.Equal(t, "2023-04-10 01:00:09 EDT", v[`filter[value][1]`][0])

			w.WriteHeader(200)
			w.Header().Set("Content-Type", "application/json")
			fmt.Fprint(w, res2)
		}

		if count == 2 {
			w.WriteHeader(200)
			w.Header().Set("Content-Type", "application/json")
			fmt.Fprint(w, empty)
		}

		count++
	})

	tc := AlchemerConnector{BaseUrl: ts.URL, PageSize: 5}

	cnf := &SourceConf{
		Name:   "",
		Source: "",
		Config: []byte(`{"survey_id": 135, "timezone": "America/New_York"}`),
	}

	config := new(AlchemerConfig)
	json.Unmarshal(cnf.Config, config)
	source := &Source{
		StudyID: "mystudy",
		Conf:    cnf,
		Credentials: &Credentials{
			Entity:  "alchemer",
			Key:     "key1",
			Details: []byte(`{"api_token": "foo", "api_token_secret": "sosecret"}`),
			Created: time.Now().UTC(),
		}}

	events := tc.GetResponses(source, config, "", 0)

	e := Sliceit(events)

	assert.Equal(t, 3, count)
	dataAssertions(t, e)
}

func TestGetResponses_PaginatesProperlyFromPreviousToken(t *testing.T) {
	empty := resData("alchemer-response-empty.json")
	res2 := resData("alchemer-response-paginated-2.json")
	count := 0
	ts, _ := TestServer(func(w http.ResponseWriter, r *http.Request) {
		v := r.URL.Query()

		if count == 0 {
			assert.Equal(t, "date_submitted", v[`filter[field][1]`][0])
			assert.Equal(t, "2023-04-10 01:00:09 EDT", v[`filter[value][1]`][0])

			w.WriteHeader(200)
			w.Header().Set("Content-Type", "application/json")
			fmt.Fprint(w, res2)
		}

		if count == 1 {

			w.WriteHeader(200)
			w.Header().Set("Content-Type", "application/json")
			fmt.Fprint(w, empty)
		}

		count++
	})

	tc := AlchemerConnector{BaseUrl: ts.URL, PageSize: 5}

	cnf := &SourceConf{
		Name:   "",
		Source: "",
		Config: []byte(`{"survey_id": 135, "timezone": "America/New_York"}`),
	}

	config := new(AlchemerConfig)
	json.Unmarshal(cnf.Config, config)
	source := &Source{
		StudyID: "mystudy",
		Conf:    cnf,
		Credentials: &Credentials{
			Entity:  "alchemer",
			Key:     "key1",
			Details: []byte(`{"api_token": "foo", "api_token_secret": "sosecret"}`),
			Created: time.Now().UTC(),
		}}

	events := tc.GetResponses(source, config, "2023-04-10 01:00:09 EDT", 10)

	e := Sliceit(events)
	assert.Equal(t, 2, count)

	// Assert proper indexing of new responses
	assert.Equal(t, 62, len(e))
	assert.Equal(t, 11, e[0].Idx)
	assert.Equal(t, 72, e[61].Idx)
}
