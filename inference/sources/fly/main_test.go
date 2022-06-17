package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"regexp"
	"strings"
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

func normalizeSpace(s string) string {
	re := regexp.MustCompile(`\s+`)
	r := re.Split(s, -1)
	return strings.Join(r, " ")
}

func dataAssertions(t *testing.T, e []*InferenceDataEvent) {

	assert.Equal(t, 45, len(e))

	assert.Equal(t, 1, e[0].Idx)
	assert.Equal(t, 10, e[9].Idx)
	assert.Equal(t, 45, e[44].Idx)

	assert.Equal(t, "21085286190ffad1248d17c4135ee56f", e[0].User.ID)
	assert.Equal(t, "21085286190ffad1248d17c4135ee56f", e[9].User.ID)
	assert.Equal(t, "9ba5db11ec6c63d22f08aade805bd363", e[44].User.ID)

	assert.Equal(t, "my_custom_dropdown_reference", e[0].Variable)
	assert.Equal(t, "my_custom_opinion_scale_reference", e[9].Variable)
	assert.Equal(t, "phone_number", e[44].Variable)

	timestamp := time.Time(time.Date(2017, time.September, 14, 22, 38, 22, 0, time.UTC))
	assert.Equal(t, timestamp, e[0].Timestamp)
	assert.Equal(t, timestamp, e[9].Timestamp)

	timestamp = time.Time(time.Date(2017, time.September, 14, 22, 27, 34, 0, time.UTC))
	assert.Equal(t, timestamp, e[44].Timestamp)

	ans := `{ "type": "text", "text": "Job opportunities" }`
	assert.Equal(t, ans, normalizeSpace(string(e[0].Value)))

	ans = `{ "type": "number", "number": 1 }`
	assert.Equal(t, ans, normalizeSpace(string(e[9].Value)))

	ans = `{ "type": "phone_number", "phone_number": "+14151234567" }`
	assert.Equal(t, ans, normalizeSpace(string(e[44].Value)))
}

func TestGetResponses_WorksWithSinglePageFromExampleJson(t *testing.T) {
	res := resData("typeform-example.json")

	ts, _ := TestServer(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "/forms/formfoo/responses", r.URL.Path)
		assert.Equal(t, "page_size=5", r.URL.RawQuery)
		assert.Equal(t, "Bearer sosecret", r.Header.Get("Authorization"))

		w.WriteHeader(200)
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprint(w, res)
	})

	tc := TypeformConnector{BaseUrl: ts.URL, Key: "sosecret", PageSize: 5}

	cnf := &SourceConf{
		Name:   "",
		Source: "",
		Config: []byte(`foo`),
	}

	events := tc.GetResponses(&Source{"mystudy", cnf}, "formfoo", "", 0)

	e := Sliceit(events)
	fmt.Printf(events)
	dataAssertions(t, e)

}

func TestGetResponses_PaginatesWhenPageIsFull(t *testing.T) {
	res1 := resData("typeform-example-pagination.json")
	res2 := resData("typeform-example-pagination-2.json")

	count := 0
	ts, _ := TestServer(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "/forms/formfoo/responses", r.URL.Path)

		if count == 0 {
			assert.Equal(t, "after=oldtoken&page_size=3", r.URL.RawQuery)
			w.WriteHeader(200)
			w.Header().Set("Content-Type", "application/json")
			fmt.Fprint(w, res1)
		}

		if count == 1 {
			assert.Equal(t, "after=5fcb3f9c162e1fcdaadff4405b741080&page_size=3", r.URL.RawQuery)

			w.WriteHeader(200)
			w.Header().Set("Content-Type", "application/json")
			fmt.Fprint(w, res2)
		}

		count++
	})

	tc := TypeformConnector{BaseUrl: ts.URL, Key: "sosecret", PageSize: 3}

	cnf := &SourceConf{
		Name:   "",
		Source: "",
		Config: []byte(`foo`),
	}

	events := tc.GetResponses(&Source{"mystudy", cnf}, "formfoo", "oldtoken", 0)

	e := Sliceit(events)
	dataAssertions(t, e)
}

func TestGetResponses_AddsHiddenFieldsAsUserMetadata(t *testing.T) {
	res := resData("typeform-example-hidden-fields.json")

	ts, _ := TestServer(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "/forms/formfoo/responses", r.URL.Path)

		w.WriteHeader(200)
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprint(w, res)
	})

	tc := TypeformConnector{BaseUrl: ts.URL, Key: "sosecret", PageSize: 5}

	cnf := &SourceConf{
		Name:   "",
		Source: "",
		Config: []byte(`foo`),
	}

	events := tc.GetResponses(&Source{"mystudy", cnf}, "formfoo", "", 0)

	e := Sliceit(events)

	assert.Equal(t, 3, len(e))
	assert.Equal(t, "21085286190ffad1248d17c4135ee56f", e[0].User.ID)
	assert.Equal(t, json.RawMessage([]byte(`"foo"`)), e[0].User.Metadata["key"])
	assert.Equal(t, "21085286190ffad1248d17c4135ee56f", e[1].User.ID)
	assert.Equal(t, json.RawMessage([]byte(`"foo"`)), e[1].User.Metadata["key"])

	assert.Equal(t, "610fc266478b41e4927945e20fe54ad2", e[2].User.ID)
	assert.Equal(t, json.RawMessage([]byte(`"bar"`)), e[2].User.Metadata["key"])
}

func TestGetResponses_StartsFromOldIdxAndIterates(t *testing.T) {
	res := resData("typeform-example.json")

	ts, _ := TestServer(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "/forms/formfoo/responses", r.URL.Path)

		w.WriteHeader(200)
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprint(w, res)
	})

	tc := TypeformConnector{BaseUrl: ts.URL, Key: "sosecret", PageSize: 5}

	cnf := &SourceConf{
		Name:   "",
		Source: "",
		Config: []byte(`foo`),
	}

	events := tc.GetResponses(&Source{"mystudy", cnf}, "formfoo", "oldtoken", 350)

	e := Sliceit(events)

	assert.Equal(t, 45, len(e))
	assert.Equal(t, 351, e[0].Idx)
	assert.Equal(t, 395, e[44].Idx)
}
