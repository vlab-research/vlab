package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"regexp"
	"strings"
	"testing"

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
	assert.Equal(t, 2, len(e))

	for i := 0; i < len(e); i++ {
		assert.Equal(t, 1, e[0].Idx)
		assert.Equal(t, 2, e[1].Idx)
	}
}

func TestGetResponses_PaginatesWhenPageIsFull(t *testing.T) {
	res1 := resData("fly_example.json")
	res2 := resData("fly_example.json")

	count := 1
	ts, _ := TestServer(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "/all", r.URL.Path)

		if count == 0 {
			assert.Equal(t, "after=oldtoken&page_size=3", r.URL.RawQuery)
			w.WriteHeader(200)
			w.Header().Set("Content-Type", "application/json")
			fmt.Fprint(w, res1)
		}

		if count == 1 {
			assert.Equal(t, "after=be5ae9dd-0189-478e-8a3d-4d8ead8240a4&page_size=3", r.URL.RawQuery)

			w.WriteHeader(200)
			w.Header().Set("Content-Type", "application/json")
			fmt.Fprint(w, res2)
		}

		count++
	})

	tc := flyConnector{BaseUrl: ts.URL, Key: "sosecret", PageSize: 3}

	cnf := &SourceConf{
		Name:   "",
		Source: "",
		Config: []byte(`foo`),
	}
	study := "1"

	events := tc.GetResponses(&Source{StudyID: study, Conf: cnf}, "formfoo", "be5ae9dd-0189-478e-8a3d-4d8ead8240a4", 0)

	e := Sliceit(events)
	dataAssertions(t, e)
}

func TestGetResponses_AddsHiddenFieldsAsUserMetadata(t *testing.T) {
	res := resData("fly_example.json")

	s := string(res)
	data := GetResponsesResponse{}
	json.Unmarshal([]byte(s), &data)

	count := 0
	ts, _ := TestServer(func(w http.ResponseWriter, r *http.Request) {

		assert.Equal(t, "/all", r.URL.Path)

		if count == 0 {
			assert.Equal(t, "other", data.Items[0].Metadata.Platform)

			w.WriteHeader(http.StatusOK)
			w.Header().Set("Content-Type", "application/json")
			fmt.Fprint(w, res)
		}

		if count == 1 {
			assert.Equal(t, "other", data.Items[1].Metadata.Platform)

			w.WriteHeader(http.StatusOK)
			w.Header().Set("Content-Type", "application/json")
			fmt.Fprint(w, res)
		}

	})
	count++

	tc := flyConnector{BaseUrl: ts.URL, Key: "sosecret", PageSize: 5}

	events := tc.GetResponses(&Source{StudyID: res}, "formfoo", "token_2", 0)
	e := Sliceit(events)

	assert.Equal(t, 2, len(e))
}

func TestGetResponses_StartsFromOldIdxAndIterates(t *testing.T) {
	res := resData("fly_example.json")

	ts, _ := TestServer(func(w http.ResponseWriter, r *http.Request) {
		fmt.Printf("Fin: %v\n", r.URL.Path)
		assert.Equal(t, "/all", r.URL.Path)

		w.WriteHeader(200)
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprint(w, res)
	})

	tc := flyConnector{BaseUrl: ts.URL, Key: "sosecret", PageSize: 5}

	events := tc.GetResponses(&Source{StudyID: res}, "formfoo", "token_3", 0)

	e := Sliceit(events)

	assert.Equal(t, 2, len(e))

	for i := 0; i < len(e); i++ {
		assert.Equal(t, 1, e[0].Idx)
		assert.Equal(t, 2, e[1].Idx)
	}

}

func TestValidateTokenIsSent(t *testing.T) {
	res := resData("fly_example.json")
	ts, _ := TestServer(func(w http.ResponseWriter, r *http.Request) {
		// fmt.Println("get token ->", r.Header.Get("Authorization"))
		assert.Equal(t, "Bearer token_123", r.Header.Get("Authorization"))

		w.WriteHeader(200)
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprint(w, res)
	})

	tc := flyConnector{BaseUrl: ts.URL, Key: "token_123", PageSize: 10}
	events := tc.GetResponses(&Source{StudyID: res}, "formfoo", "token_4", 0)

	e := Sliceit(events)

	assert.Equal(t, 2, len(e))
}
