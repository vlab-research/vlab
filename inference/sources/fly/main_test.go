package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"reflect"
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

func dataAssertions(t *testing.T, e []*InferenceDataEvent) {
	assert.Equal(t, 4, len(e))

	assert.Equal(t, 1, e[0].Idx)
	assert.Equal(t, 2, e[1].Idx)
	assert.Equal(t, 3, e[2].Idx)

}

func TestGetResponses_PaginatesWhenPageIsFull(t *testing.T) {
	res1 := resData("fly_example.json")
	res2 := resData("fly_example2.json")

	s := string(res1)
	data := GetResponsesResponse{}
	json.Unmarshal([]byte(s), &data)

	s2 := string(res2)
	data2 := GetResponsesResponse{}
	json.Unmarshal([]byte(s2), &data2)

	lastToken := data.Items[len(data.Items)-1]

	count := 1
	ts, _ := TestServer(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "/all", r.URL.Path)
		if count == 1 {
			// assert.Equal(t, "after=4viu4r8djwxwb2udbivx42avnawwj5wj&page_size=1", r.URL.RawQuery)
			assert.Equal(t, "4viu4r8djwxwb2udbivx42avnawwj5wj", r.URL.Query().Get("after"))

			w.Header().Set("Content-Type", "application/json")
			fmt.Fprint(w, res1)
		}
	})

	tc := flyConnector{BaseUrl: ts.URL, Key: "sosecret", PageSize: 1}

	events := tc.GetResponses(&Source{StudyID: res1}, "formfoo", lastToken.Token, 0)

	e := Sliceit(events)
	assert.Equal(t, 4, len(e))

	lastTokenPosition := len(e) - 1

	count++

	// PAGE #2
	if count == 2 {
		assert.Condition(t, func() bool {
			for i := range data2.Items {
				// Searches the entire array
				fmt.Println("data2.Items[i].Token ->", data2.Items[i].Token)
				if data2.Items[i].Token == e[lastTokenPosition].Pagination {
					// Found!
					return true
				}
			}
			return false
		}, "token does not match expected")
	}

}

func TestGetResponses_AddsHiddenFieldsAsUserMetadata(t *testing.T) {
	res := resData("fly-example-hidden-fields.json")

	s := string(res)
	data := GetResponsesResponse{}
	json.Unmarshal([]byte(s), &data)

	ts, _ := TestServer(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "/all", r.URL.Path)

		w.WriteHeader(200)
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprint(w, res)
	})

	tc := flyConnector{BaseUrl: ts.URL, Key: "sosecret", PageSize: 5}

	cnf := &SourceConf{
		Name:   "",
		Source: "",
		Config: []byte(`foo`),
	}

	events := tc.GetResponses(&Source{"mystudy", cnf}, "formfoo", "", 0)

	e := Sliceit(events)

	assert.Equal(t, 3, len(e))
	assert.Equal(t, "126", e[0].User.ID)
	assert.Equal(t, json.RawMessage([]byte(`"foo"`)), e[0].User.Metadata["key"])
	assert.Equal(t, "127", e[1].User.ID)
	assert.Equal(t, json.RawMessage([]byte(`"bar"`)), e[1].User.Metadata["key"])

	assert.Equal(t, "128", e[2].User.ID)
	assert.Equal(t, json.RawMessage([]byte(`"baz"`)), e[2].User.Metadata["key"])
}

func TestGetResponses_StartsFromOldIdxAndIterates(t *testing.T) {
	res := resData("fly_example.json")
	res2 := resData("fly_example2.json")

	s := string(res)
	data := GetResponsesResponse{}
	json.Unmarshal([]byte(s), &data)

	s2 := string(res2)
	data2 := GetResponsesResponse{}
	json.Unmarshal([]byte(s2), &data2)

	ts, _ := TestServer(func(w http.ResponseWriter, r *http.Request) {
		fmt.Printf("Fin: %v\n", r.URL.Path)
		assert.Equal(t, "/all", r.URL.Path)

		w.WriteHeader(200)
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprint(w, res)
	})

	tc := flyConnector{BaseUrl: ts.URL, Key: "sosecret", PageSize: 5}

	events := tc.GetResponses(&Source{StudyID: res}, "formfoo", "token_3", 0)
	events2 := tc.GetResponses(&Source{StudyID: res2}, "formfoo", "token_3", 0)

	e := Sliceit(events)

	e2 := Sliceit(events2)

	assert.Equal(t, 4, len(e))
	assert.Equal(t, 4, len(e2))

	lastIndex := len(e) - 1

	// Last idx
	assert.Equal(t, "9ba5db11ec6c63d22f08aade805bd363", e[lastIndex].Pagination)

	// fmt.Println("data.Items ->", data.Items)
	// fmt.Println("data2.Items ->", data2.Items)

	list1 := data.Items
	list2 := data2.Items

	list3 := list1

	// Concatenation of items
	for index := range list2 {
		list3 = append(list3, list2[index])
	}
	s3 := string(res)
	data3 := GetResponsesResponse{}
	json.Unmarshal([]byte(s3), &data3)

	assert.Condition(t, func() bool {
		for i := range list3 {
			// Searches the entire array
			if list3[i].Parent_surveyid == e[lastIndex].Pagination {

				totalItems := len(list3)

				// Iterate an array at a specific position "list3[5:8]"
				startFromLastPosition := list3[i:totalItems]

				for v := range startFromLastPosition {
					fmt.Println("startFromOldIdxAndIterates: ", startFromLastPosition[v].Parent_surveyid)
				}
				// Found!
				return true
			}
		}
		return false
	}, "Idx does not match expected")

}

func TestValidateTokenIsSent(t *testing.T) {
	res := resData("fly_example.json")
	type GetTokenResponse struct {
		AccessToken string `json:"access_token"`
	}

	tt := flyConnector{
		BaseUrl:      "",
		Key:          "",
		PageSize:     0,
		ClientId:     "P0F1mNGTyOfAFEvgZEtjRHVBEEmzIyPi",
		ClientSecret: "TXt1afXrWQitQxfKR4MwSdhPc5puWMiqXrv1Wmx64VluJM-xLgoFYfVa5neVieg5",
	}
	tokenResponse := tt.GetToken()

	s := string(tokenResponse)
	tokenStructure := GetTokenResponse{}
	json.Unmarshal([]byte(s), &tokenStructure)

	token := tokenStructure.AccessToken
	tokenType := reflect.TypeOf(token)

	// fmt.Println("token ->", token)

	ts, _ := TestServer(func(w http.ResponseWriter, r *http.Request) {
		assert.Condition(t, func() bool {
			// fmt.Println("token ->", token)
			if token == "" {
				return token != ""
			}
			return true
		}, "Token is required")

		assert.Equal(t, reflect.TypeOf(""), tokenType)
		assert.Equal(t, "Bearer "+token, r.Header.Get("Authorization"))

		w.WriteHeader(http.StatusOK)
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprint(w, res)
	})

	tc := flyConnector{BaseUrl: ts.URL, Key: token, PageSize: 10}
	events := tc.GetResponses(&Source{StudyID: res}, "formfoo", "token_4", 0)

	e := Sliceit(events)

	assert.Equal(t, 4, len(e))
}
