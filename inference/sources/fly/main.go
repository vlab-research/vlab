package main

import (
	"fmt"
	"log"
	"net/http"

	"github.com/caarlos0/env/v6"
	"github.com/dghubble/sling"
	. "github.com/vlab-research/vlab/inference/inference-data"
)

func handle(err error) {
	if err != nil {
		log.Fatal(err)
	}
}

type GetResponsesParams struct {
	PageSize int    `url:"page_size"`
	After    string `url:"after,omitempty"`
}

type GetResponsesResponse struct {
	TotalItems int `json:"total_items"`
	PageCount  int `json:"page_count"`
	Items      []struct {
		Parent_surveyid  string `json:"parent_surveyid"`
		Parent_shortcode string `json:"parent_shortcode"`
		Surveyid         string `json:"Surveyid"`
		flowid           string `json:"flowid"`
		Userid           string `json:"Userid"`
		Question_ref     string `json:"question_ref"`
		Question_idx     string `json:"question_idx"`
		Question_text    string `json:"question_text"`
		Response         struct {
			Text string `json:"user_agent"`
		} `json:"metadata"`
		Timestamp           string `json:"timestamp"`
		metadata            string `json:"metadata"`
		pageid              string `json:"metadata"`
		translated_response string `json:"metadata"`
	} `json:"items"`
}

type flyConnector struct {
	BaseUrl  string `env:"FLY_BASE_URL,required"`
	Key      string `env:"FLY_KEY,required"`
	PageSize int    `env:"FLY_PAGE_SIZE,required"`
}

type TypeformError struct {
	Code string `json:"code"`
}

func (e *TypeformError) Empty() bool {
	return e.Code == ""
}

func (e *TypeformError) Error() string {
	return e.Code
}

func (c flyConnector) loadEnv() flyConnector {
	err := env.Parse(&c)
	handle(err)
	return c
}

func Call(client *http.Client, baseUrl string, key string, form string, params *GetResponsesParams) (*GetResponsesResponse, error) {
	sli := sling.New().Client(client).Base(baseUrl).Set("Accept", "application/json").Set("Authorization", fmt.Sprintf("Bearer %s", key))
	res := new(GetResponsesResponse)
	apiError := new(TypeformError)
	_, err := sli.Get("flys/api/v1/").QueryStruct(params).Receive(res, apiError)

	if err != nil {
		return nil, err
	}

	if !apiError.Empty() {
		return nil, apiError
	}
	return res, nil
}

func (c flyConnector) GetResponses(source *Source, form string, token string, idx int) <-chan *InferenceDataEvent {
	events := make(chan *InferenceDataEvent)
	params := &GetResponsesParams{PageSize: c.PageSize, After: token}
	client := &http.Client{}
	go func() {
		defer close(events)
		// for loop to paginate here?
		params.After = token
		for {
			res, err := Call(client, c.BaseUrl, c.Key, form, params)

			if err != nil {
				handle(err)
			}

			for _, item := range res.Items {
				fmt.Printf("response: %v\n \n", item.Surveyid)
				//Todo:  sabe database
				params.After = item.pageid
				idx++
				event := &InferenceDataEvent{
					User:       User{ID: item.pageid},
					Study:      source.StudyID,
					SourceConf: source.Conf,
					Idx:        idx,
				}
				events <- event
			}

			if res.TotalItems == 2 {
				break
			}

		}
	}()

	return events
}

func (c flyConnector) Handler(source *Source, lastEvent *InferenceDataEvent) <-chan *InferenceDataEvent {
	return nil
}

func Sliceit[T any](c <-chan T) []T {
	s := []T{}
	for x := range c {
		s = append(s, x)
	}
	return s
}

func main() {
	// todo: temporarily  flyConnector
	c := flyConnector{
		BaseUrl:  "",
		Key:      "",
		PageSize: 1,
	}
	c.loadEnv()

	cnf := &SourceConf{
		Name:   "",
		Source: "",
		Config: []byte(`foo`),
	}

	events := c.GetResponses(&Source{"flys", cnf}, "formfoo", "oldtoken", 350)
	e := Sliceit(events)
	fmt.Printf("Fin: %v\n", e)
}
