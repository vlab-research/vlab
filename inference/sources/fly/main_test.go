package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"regexp"
	"strconv"
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
	res2 := resData("fly_example2.json")

	s := string(res1)
	data := GetResponsesResponse{}
	json.Unmarshal([]byte(s), &data)

	s2 := string(res2)
	data2 := GetResponsesResponse{}
	json.Unmarshal([]byte(s2), &data2)

	count := 1
	// Supongamos que 2 es el limite de items por page
	full_page_with_items := 2
	ts, _ := TestServer(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "/all", r.URL.Path)
		if count == 1 {
			assert.Equal(t, "after=be5ae9dd-0189-478e-8a3d-4d8ead8240a4&page_size=1", r.URL.RawQuery)
			page_size, err := strconv.Atoi(r.URL.Query().Get("page_size"))

			if err != nil {
				log.Fatal(err)
			}
			assert.Equal(t, count, page_size)

			// PAGE #1
			assert.Equal(t, count, data.PageCount)
			// assert.Equal(t, full_page_with_items, data.TotalItems-1)

			assert.Condition(t, func() bool {
				if full_page_with_items < data.TotalItems {
					return full_page_with_items > data.TotalItems
				}
				return true
			}, "Crearé una nueva página")

			w.Header().Set("Content-Type", "application/json")
			fmt.Fprint(w, res1)
		}

		count++

		if count == 2 {
			// PAGE #2
			assert.Equal(t, count, data2.PageCount)
			assert.Equal(t, 1, data2.TotalItems)

			// page_size, err := strconv.Atoi(r.URL.Query().Get("page_size"))
			// if err != nil {
			// 	log.Fatal(err)
			// }
			// Si el usuario quiere ir a la segunda pagina pero no existe:
			// fmt.Println("data.TotalItems ->", data.TotalItems)
			// assert.Condition(t, func() bool {
			// 	if full_page <= data.TotalItems {
			// 		return full_page >= data.TotalItems
			// 	}
			// 	return true
			// }, "Crearé una nueva pagina")

			w.Header().Set("Content-Type", "application/json")
		}
	})
	// Establecer el size de la pagina
	tc := flyConnector{BaseUrl: ts.URL, Key: "sosecret", PageSize: 1}

	events := tc.GetResponses(&Source{StudyID: res1}, "formfoo", "be5ae9dd-0189-478e-8a3d-4d8ead8240a4", 0)

	e := Sliceit(events)
	assert.Equal(t, 3, len(e))
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

		count++

		if count == 1 {
			assert.Equal(t, "other", data.Items[1].Metadata.Platform)
			w.Header().Set("Content-Type", "application/json")
			fmt.Fprint(w, res)
		}
	})

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
