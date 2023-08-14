package main

import (
	"encoding/json"
	"fmt"
	"github.com/stretchr/testify/assert"
	. "github.com/vlab-research/vlab/inference/inference-data"
	. "github.com/vlab-research/vlab/inference/test-helpers"
	"net/http"
	"testing"
	"time"
	"io/ioutil"
	"strings"
)

func check(e error) {
	if e != nil {
		panic(e)
	}
}

func TestCreateExport_GetsAnExportLinkWhenFinished(t *testing.T) {
	calls := 0

	ts, _ := TestServer(func(w http.ResponseWriter, r *http.Request) {

		assert.Equal(t, "testtoken", r.Header.Get("X-API-TOKEN"))

		if calls == 0 {
			assert.Equal(t, "/API/v3/surveys/foo/export-responses", r.URL.Path)

			b, _ := ioutil.ReadAll(r.Body)
			s := strings.TrimSpace(string(b))

			exp := `{"format":"json","sortByLastModifiedDate":true,"allowContinuation":true}`
			assert.Equal(t, s, exp)

			res := `{"result":{"progressId":"PROGRESSID","percentComplete":0.0,"status":"inProgress"},"meta":{"requestId":"92abd129-c221-4231-beb6-be81b9e49dc3","httpStatus":"200 - OK"}}`

			w.WriteHeader(200)
			w.Header().Set("Content-Type", "application/json")
			fmt.Fprint(w, res)
		}

		if calls > 0 && calls < 3 {
			res := `{"result":{"fileId":"ed6bf88e-5c49-4d64-8edd-33bdf7cda658-def","percentComplete":50.0,"status":"not complete"},"meta":{"requestId":"36c0f2df-d64c-4a7d-9a9f-6a3a8a1ac4ef","httpStatus":"200 - OK"}}`
			fmt.Fprint(w, res)

		}

		if calls == 3 {
			res := `{"result":{"fileId":"FILEID","percentComplete":100.0,"status":"complete","continuationToken": "foo-continue"},"meta":{"requestId":"36c0f2df-d64c-4a7d-9a9f-6a3a8a1ac4ef","httpStatus":"200 - OK"}}`
			fmt.Fprint(w, res)
		}

		calls++
	})


	sli := MakeSling(http.DefaultClient, ts.URL, "testtoken")
	pagination, res, err := CreateExport(sli, "foo", 0.01, 5, "") 

	assert.Nil(t, err)
	assert.Equal(t, 4, calls)
	assert.Equal(t, "foo-continue", pagination)
	assert.Equal(t, "/API/v3/surveys/foo/export-responses/FILEID/file", res)
}

func TestCreateExport_QuitsAfterTryingAWhile(t *testing.T) {
	calls := 0
	ts, _ := TestServer(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "testtoken", r.Header.Get("X-API-TOKEN"))

		if calls == 0 {
			assert.Equal(t, "/API/v3/surveys/foo/export-responses", r.URL.Path)

			res := `{"result":{"progressId":"PROGRESSID","percentComplete":0.0,"status":"inProgress"},"meta":{"requestId":"92abd129-c221-4231-beb6-be81b9e49dc3","httpStatus":"200 - OK"}}`

			w.WriteHeader(200)
			w.Header().Set("Content-Type", "application/json")
			fmt.Fprint(w, res)
		}

		if calls > 0 {
			res := `{"result":{"fileId":"ed6bf88e-5c49-4d64-8edd-33bdf7cda658-def","percentComplete":50.0,"status":"not complete"},"meta":{"requestId":"36c0f2df-d64c-4a7d-9a9f-6a3a8a1ac4ef","httpStatus":"200 - OK"}}`
			fmt.Fprint(w, res)

		}
		calls++
	})

	sli := MakeSling(http.DefaultClient, ts.URL, "testtoken") 
	_, _, err := CreateExport(sli, "foo", 0.01, 10, "")

	assert.NotNil(t, err)
	assert.Equal(t, 11, calls)
	assert.Contains(t, err.Error(), "foo")
}

func TestCreateExport_SendsContinuationTokenIfItHasOneAndGetsNewOneBack(t *testing.T) {
	calls := 0

	ts, _ := TestServer(func(w http.ResponseWriter, r *http.Request) {

		assert.Equal(t, "testtoken", r.Header.Get("X-API-TOKEN"))

		if calls == 0 {
			assert.Equal(t, "/API/v3/surveys/foo/export-responses", r.URL.Path)

			b, _ := ioutil.ReadAll(r.Body)
			s := strings.TrimSpace(string(b))

			exp := `{"format":"json","sortByLastModifiedDate":true,"continuationToken":"foo-continue"}`
			assert.Equal(t, s, exp)

			res := `{"result":{"progressId":"PROGRESSID","percentComplete":0.0,"status":"inProgress"},"meta":{"requestId":"92abd129-c221-4231-beb6-be81b9e49dc3","httpStatus":"200 - OK"}}`

			w.WriteHeader(200)
			w.Header().Set("Content-Type", "application/json")
			fmt.Fprint(w, res)
		}

		if calls > 0 {
			res := `{"result":{"fileId":"FILEID","percentComplete":100.0,"status":"complete","continuationToken": "bar-continue"},"meta":{"requestId":"36c0f2df-d64c-4a7d-9a9f-6a3a8a1ac4ef","httpStatus":"200 - OK"}}`
			fmt.Fprint(w, res)
		}
		calls++
	})

	sli := MakeSling(http.DefaultClient, ts.URL, "testtoken")
	pagination, _, err := CreateExport(sli, "foo", 0.01, 5, "foo-continue")

	assert.Nil(t, err)
	assert.Equal(t, "bar-continue", pagination)
}

func TestReadZipFile_Works(t *testing.T) {
	res, err := ReadZippedJSON("test/responses.zip") 

	assert.Nil(t, err)

	assert.NotNil(t, res)

	assert.Equal(t, "R_D6MNkLFwmf97OEh", res.Responses[0].ResponseID)
	assert.Equal(t, json.RawMessage([]byte(`"2023-06-30T22:15:17.777Z"`)), res.Responses[1].Values["recordedDate"])
	assert.Equal(t, 30, res.Responses[1].RecordedDate.Day())
	assert.Equal(t, time.Month(6), res.Responses[1].RecordedDate.Month())

}

func dataAssertions(t *testing.T, e []*InferenceDataEvent) {
	lookup := MakeUserMap(e)

	assert.Equal(t, 298, len(e))
	assert.Equal(t, `{"label":"True","value":1}`, string(lookup["R_3m2KLxy0BqJEfi7"]["finished"].Value))
	assert.Equal(t, `{"label":"Male","value":1}`, string(lookup["R_3m2KLxy0BqJEfi7"]["QID61"].Value))

	assert.Equal(t, `{"label":"","value":"123456789"}`, string(lookup["R_3m2KLxy0BqJEfi7"]["vlab_id"].Value))
	assert.Equal(t, `{"label":"","value":"202307071"}`, string(lookup["R_UPJj7TrnmrtWDpT"]["vlab_id"].Value))

	assert.Equal(t, "foo-continue", e[0].Pagination)
	assert.Equal(t, "foo-continue", e[297].Pagination)
}

func TestGetResponsesFromFile_GetsAllResponses(t *testing.T) {

	cnf := &SourceConf{
		Name:   "",
		Source: "",
		Config: []byte(`{"survey_id": "foosurvey"}`),
	}

	source := &Source{
		StudyID: "mystudy",
		Conf:    cnf,
		Credentials: &Credentials{
			Entity:  "qualtrics",
			Key:     "key1",
			Details: []byte(`{"api_token": "foo", "api_token_secret": "sosecret"}`),
			Created: time.Now().UTC(),
		}}

	events := GetResponsesFromFile(source, "test/responses.zip", 0, "foo-continue")

	e := Sliceit(events)
	dataAssertions(t, e)
}
