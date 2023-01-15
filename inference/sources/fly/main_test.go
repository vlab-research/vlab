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
