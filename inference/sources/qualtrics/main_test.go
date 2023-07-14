package main

import (
	"fmt"
	"net/http"

	"github.com/stretchr/testify/assert"

	. "github.com/vlab-research/vlab/inference/test-helpers"
	"testing"
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
			res := `{"result":{"fileId":"FILEID","percentComplete":100.0,"status":"complete"},"meta":{"requestId":"36c0f2df-d64c-4a7d-9a9f-6a3a8a1ac4ef","httpStatus":"200 - OK"}}`
			fmt.Fprint(w, res)
		}

		calls++
	})

	res, err := CreateExport(http.DefaultClient, ts.URL, "foo", "testtoken")

	assert.Nil(t, err)
	assert.Equal(t, 4, calls)
	assert.Equal(t, "/API/v3/surveys/foo/export-responses/FILEID/file", res)

}
