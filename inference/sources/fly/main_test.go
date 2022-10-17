package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
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

	ans := `{"Response":"last","Translated_response":"último"}`
	assert.Equal(t, ans, string(e[0].Value))
	ans = `{"Response":"first","Translated_response":"primero"}`
	ans = `{"Response":"hello","Translated_response":"hola"}`
	assert.Equal(t, ans, string(e[7].Value))
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

	// lastToken := data.Items[len(data.Items)-1]

	count := 0
	ts, _ := TestServer(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "/all", r.URL.Path)
		after := r.URL.Query().Get("after")

		if count == 0 {
			assert.Condition(t, func() bool {
				if after == "" {
					return after != ""
				}
				return true
			}, "No token sent")

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
		}

		count++

	})

	tc := flyConnector{BaseUrl: ts.URL, Key: "sosecret", PageSize: 2}

	events := tc.GetResponses(&Source{StudyID: res1}, "formfoo", "oldtoken", 0)

	e := Sliceit(events)
	dataAssertions(t, e)
}

func TestGetResponses_AddsHiddenFieldsAsUserMetadata(t *testing.T) {
	res := resData("fly_example.json")

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

	events := tc.GetResponses(&Source{"mystudy", cnf}, "formfoo", "124121d12", 0)

	e := Sliceit(events)

	assert.Equal(t, 4, len(e))
	assert.Equal(t, "126", e[0].User.ID)
	// assert.Equal(t, json.RawMessage([]byte(`"foo"`)), e[0].User.Metadata["key"])
	assert.Equal(t, "127", e[1].User.ID)
	// assert.Equal(t, json.RawMessage([]byte(`"bar"`)), e[1].User.Metadata["key"])
	assert.Equal(t, "128", e[2].User.ID)
	// assert.Equal(t, json.RawMessage([]byte(`"baz"`)), e[2].User.Metadata["key"])
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

	events := tc.GetResponses(&Source{StudyID: res}, "formfoo", "9ba5db11ec6c63d22f08aade805bd363", 15)

	e := Sliceit(events)

	assert.Equal(t, 16, e[0].Idx)

	lastIndex := len(e) - 1

	// Last idx
	// assert.Equal(t, "9ba5db11ec6c63d22f08aade805bd363", e[lastIndex].Pagination)
	assert.Equal(t, "4viu4r8djwxwb2udbivx42avnawwj5wj", e[lastIndex].Pagination)

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
			// fmt.Println("list3[i].Token ->", list3[i].Token)

			// Searches the entire array
			if list3[i].Token == e[lastIndex].Pagination {

				totalItems := len(list3)

				// Iterate an array at a specific position "list3[5:8]"
				startFromLastPosition := list3[i:totalItems]

				fmt.Println("Remaining items:")
				for v := range startFromLastPosition {
					fmt.Println("startFromOldIdxAndIterates: ", startFromLastPosition[v].Token)
				}
				// Found!
				return true
			}
		}
		return false
	}, "Idx does not match expected")

}

// func TestValidateTokenIsSent(t *testing.T) {
// 	res := resData("fly_example.json")
// 	type GetTokenResponse struct {
// 		AccessToken string `json:"access_token"`
// 	}

// 	tt := flyConnector{}

// 	clientId := "P0F1mNGTyOfAFEvgZEtjRHVBEEmzIyPi"
// 	clientSecret := "TXt1afXrWQitQxfKR4MwSdhPc5puWMiqXrv1Wmx64VluJM-xLgoFYfVa5neVieg5"

// 	tokenResponse := tt.GetToken(clientId, clientSecret)

// 	s := string(tokenResponse)
// 	tokenStructure := GetTokenResponse{}
// 	json.Unmarshal([]byte(s), &tokenStructure)

// 	token := tokenStructure.AccessToken
// 	tokenType := reflect.TypeOf(token)

// 	ts, _ := TestServer(func(w http.ResponseWriter, r *http.Request) {
// 		assert.Condition(t, func() bool {
// 			// fmt.Println("token ->", token)
// 			if token == "" {
// 				return token != ""
// 			}
// 			return true
// 		}, "Token is required")

// 		assert.Equal(t, reflect.TypeOf(""), tokenType)
// 		assert.Equal(t, "Bearer "+token, r.Header.Get("Authorization"))

// 		w.WriteHeader(http.StatusOK)
// 		w.Header().Set("Content-Type", "application/json")
// 		fmt.Fprint(w, res)
// 	})

// 	tc := flyConnector{BaseUrl: ts.URL, Key: token, PageSize: 10}
// 	events := tc.GetResponses(&Source{StudyID: res}, "formfoo", "token_4", 0)

// 	e := Sliceit(events)

// 	assert.Equal(t, 4, len(e))
// }

func TestGetAuthTokenMakesAudience(t *testing.T) {
	ts, _ := TestServer(func(w http.ResponseWriter, r *http.Request) {
		expected := `{"client_id":"id","client_secret":"secret","audience":"https://dev-x7eacpbs.us.auth0.com/api/v2","grant_type":"client_credentials"}`
		data, err := ioutil.ReadAll(r.Body)
		dat := strings.TrimSpace(string(data))

		assert.Nil(t, err)
		assert.Equal(t, "/oauth/token", r.URL.Path)
		assert.Equal(t, expected, dat)

		w.WriteHeader(http.StatusOK)
		w.Header().Set("Content-Type", "application/json")

		fmt.Fprintf(w, `{"token_type": "Bearer", "access_token": "foobarbaz", "expires_in": 14400}`)
	})

	svc := &Service{AuthUrl: ts.URL, BaseUrl: "https://dev-x7eacpbs.us.auth0.com/api/v2", Client: &http.Client{}}
	err := svc.Auth("id", "secret")

	assert.Nil(t, err)
	assert.Equal(t, "foobarbaz", svc.Token.AccessToken)
}
