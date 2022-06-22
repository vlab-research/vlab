package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	"github.com/caarlos0/env/v6"
	"github.com/dghubble/sling"
	"github.com/tidwall/sjson"
	"github.com/vlab-research/vlab/inference/connector"
	. "github.com/vlab-research/vlab/inference/inference-data"
)

func handle(err error) {
	if err != nil {
		log.Fatal(err)
	}
}

type TypeformConfig struct {
	FormID string `json:"form_id"`
}

type GetResponsesParams struct {
	PageSize int    `url:"page_size"`
	After    string `url:"after,omitempty"`
}

type Field struct {
	ID   string `json:"id"`
	Type string `json:"type"`
	Ref  string `json:"ref"`
}

type Answer struct {
	Field Field  `json:"field"`
	Type  string `json:"type"`
}

type GetResponsesResponse struct {
	TotalItems int `json:"total_items"`
	PageCount  int `json:"page_count"`
	Items      []struct {
		LandingID   string    `json:"landing_id"`
		Token       string    `json:"token"`
		LandedAt    time.Time `json:"landed_at"`
		SubmittedAt time.Time `json:"submitted_at"`
		Metadata    struct {
			UserAgent string `json:"user_agent"`
			Platform  string `json:"platform"`
			Referer   string `json:"referer"`
			NetworkID string `json:"network_id"`
			Browser   string `json:"browser"`
		} `json:"metadata"`
		Answers    []json.RawMessage          `json:"answers"`
		Hidden     map[string]json.RawMessage `json:"hidden"` // TODO: is this the format???
		Calculated struct {
			Score int `json:"score"`
		} `json:"calculated"`
		Variables []struct {
			Key    string `json:"key"`
			Type   string `json:"type"`
			Number int    `json:"number,omitempty"`
			Text   string `json:"text,omitempty"`
		} `json:"variables"`
	} `json:"items"`
}

type TypeformConnector struct {
	BaseUrl  string `env:"TYPEFORM_BASE_URL,required"`
	Key      string `env:"TYPEFORM_KEY,required"`
	PageSize int    `env:"TYPEFORM_PAGE_SIZE,required"`
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

func (c TypeformConnector) loadEnv() TypeformConnector {
	err := env.Parse(&c)
	handle(err)
	return c
}

func Call(client *http.Client, baseUrl string, key string, form string, params *GetResponsesParams) (*GetResponsesResponse, error) {

	// TODO: move out of here and into TypeformConnector
	sli := sling.New().Client(client).Base(baseUrl).Set("Accept", "application/json").Set("Authorization", fmt.Sprintf("Bearer %s", key))

	res := new(GetResponsesResponse)
	apiError := new(TypeformError)

	_, err := sli.Get("/asdflkas/").QueryStruct(params).Receive(res, apiError)

	if err != nil {
		return nil, err
	}

	if !apiError.Empty() {
		return nil, apiError
	}

	return res, nil
}

func (c TypeformConnector) GetResponses(source *Source, form string, token string, idx int) <-chan *InferenceDataEvent {
	events := make(chan *InferenceDataEvent)
	params := &GetResponsesParams{PageSize: c.PageSize, After: token}

	client := &http.Client{}

	go func() {
		defer close(events)

		// for loop to paginate here
		params.After = token

		for {
			res, err := Call(client, c.BaseUrl, c.Key, form, params)

			if err != nil {
				handle(err)
			}

			for _, item := range res.Items {

				// for pagination
				params.After = item.Token

				// Add referrer and other item.Metadata stuff???
				md := item.Hidden

				for _, dat := range item.Answers {
					var ans Answer
					err := json.Unmarshal(dat, &ans)
					if err != nil {
						handle(err)
					}

					rawAns, err := sjson.Delete(string(dat), "field")
					if err != nil {
						handle(err)
					}

					idx++
					event := &InferenceDataEvent{
						User:       User{ID: item.Token, Metadata: md},
						Study:      source.StudyID,
						SourceConf: source.Conf,
						Timestamp:  item.SubmittedAt,
						Variable:   ans.Field.Ref,
						Value:      []byte(rawAns),
						Idx:        idx,
						Pagination: item.Token,
					}
					events <- event
				}
			}

			if res.TotalItems < params.PageSize {
				// implies no more responses?
				break
			}

		}
	}()

	return events
}

func (c TypeformConnector) Handler(source *Source, lastEvent *InferenceDataEvent) <-chan *InferenceDataEvent {
	typeformConfig := new(TypeformConfig)
	err := json.Unmarshal(source.Conf.Config, typeformConfig)
	handle(err)

	log.Println("Typeform connector getting data for: ", typeformConfig)

	token := ""
	idx := 0

	if lastEvent != nil {
		token = lastEvent.Pagination
		idx = lastEvent.Idx
	}

	events := c.GetResponses(source, typeformConfig.FormID, token, idx)
	return events
}

func Sliceit[T any](c <-chan T) []T {
	s := []T{}
	for x := range c {
		s = append(s, x)
	}
	return s
}

func main() {
	c := TypeformConnector{
		BaseUrl:  "https://demo6926047.mockable.io/dosdebuche",
		Key:      "2",
		PageSize: 1,
	}
	c.loadEnv()

	// cnf := &SourceConf{
	// 	Name:   "",
	// 	Source: "",
	// 	Config: []byte(`foo`),
	// }

	// events := c.Handler(&Source{"typeform", cnf}, "formfoo", "oldtoken", 350)
	// e := Sliceit(events)

	// fmt.Printf("Fin: %v\n", e)

	connector.LoadEvents(c, "typeform", "idx")
}
