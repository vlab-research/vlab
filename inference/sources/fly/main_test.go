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
		assert.Equal(t, "/flys/api/v1/", r.URL.Path)

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

	ts, _ := TestServer(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "/flys/api/v1/", r.URL.Path)

		w.WriteHeader(200)
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprint(w, res)
	})

	tc := flyConnector{BaseUrl: ts.URL, Key: "sosecret", PageSize: 5}

	events := tc.GetResponses(&Source{StudyID: res}, "formfoo", "", 0)
	e := Sliceit(events)

	s := string(res)
	data := GetResponsesResponse{}
	json.Unmarshal([]byte(s), &data)
	// fmt.Println("Operation: ", data.Items)
	assert.Equal(t, 2, len(e))
	for i := 0; i < len(e); i++ {
		assert.Equal(t, "be5ae9dd-0189-478e-8a3d-4d8ead8240a4", data.Items[0].Surveyid)
		assert.Equal(t, "foo", data.Items[0].Metadata.Text)
		assert.Equal(t, "c3c1d340-2335-492b-bb4f-6c0cccc2735f", data.Items[1].Surveyid)
		assert.Equal(t, "bar", data.Items[1].Metadata.Text)
	}

}

func TestGetResponses_StartsFromOldIdxAndIterates(t *testing.T) {
	res := resData("fly_example.json")

	ts, _ := TestServer(func(w http.ResponseWriter, r *http.Request) {
		fmt.Printf("Fin: %v\n", r.URL.Path)
		assert.Equal(t, "/flys/api/v1/", r.URL.Path)

		w.WriteHeader(200)
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprint(w, res)
	})

	tc := flyConnector{BaseUrl: ts.URL, Key: "sosecret", PageSize: 5}

	events := tc.GetResponses(&Source{StudyID: res}, "formfoo", "", 0)
	// events := tc.GetResponses(&Source{"StudyID", cnf}, "formfoo", "oldtoken", 350)

	e := Sliceit(events)

	assert.Equal(t, 2, len(e))

	for i := 0; i < len(e); i++ {
		assert.Equal(t, 1, e[0].Idx)
		assert.Equal(t, 2, e[1].Idx)
	}

}
