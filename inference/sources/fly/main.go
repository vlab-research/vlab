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

type flyConfig struct {
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

type GetResponsesResponse []struct {
	ParentSurveyid string `json:"parent_surveyid"`
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
	fmt.Printf("-->>Error: %v\n", err)
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
		params.After = token
		res, err := Call(client, c.BaseUrl, c.Key, form, params)
		fmt.Printf("res esto es la respuesta del servicio-->: %v\n \n", res)

		if err != nil {
			handle(err)
		}

		// for _, item := range res.Pageid {
		// fmt.Printf("%v\n", item)

		// for pagination
		// params.After = item.ParentSurveyid

		// Add referrer and other item.Metadata stuff???
		// md := item.Hidden

		// for _, dat := range item.Answers {
		// 	var ans Answer
		// 	err := json.Unmarshal(dat, &ans)
		// 	if err != nil {
		// 		handle(err)
		// 	}

		// 	rawAns, err := sjson.Delete(string(dat), "field")
		// 	if err != nil {
		// 		handle(err)
		// 	}

		// 	idx++
		// 	event := &InferenceDataEvent{
		// 		User:       User{ID: item.Token, Metadata: md},
		// 		Study:      source.StudyID,
		// 		SourceConf: source.Conf,
		// 		Timestamp:  item.SubmittedAt,
		// 		Variable:   ans.Field.Ref,
		// 		Value:      []byte(rawAns),
		// 		Idx:        idx,
		// 		Pagination: item.Token,
		// 	}
		// 	events <- event
		// }
		// }

		// if res.TotalItems < params.PageSize {
		// 	// implies no more responses?
		// 	break
		// }

		// }
	}()

	return events
}

func (c flyConnector) Handler(source *Source, lastEvent *InferenceDataEvent) <-chan *InferenceDataEvent {
	// flyConfig := new(flyConfig)

	// fmt.Printf("FIN@esto es nullde Handler: %v\n", flyConfig)

	// err := json.Unmarshal(source.Conf.Config, flyConfig)

	// handle(err)

	// log.Println("Typeform connector getting data for: ", flyConfig)

	// token := ""
	// idx := 0

	// if lastEvent != nil {
	// 	token = lastEvent.Pagination
	// 	idx = lastEvent.Idx
	// }

	// events := c.GetResponses(source, flyConfig.FormID, token, idx)

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
	c := flyConnector{
		BaseUrl:  "https://demo6926047.mockable.io/flys",
		Key:      "parent_shortcode",
		PageSize: 1,
	}
	// fmt.Printf("-->>esto es nullde lastEvent: %v\n", c.BaseUrl)
	c.loadEnv()

	cnf := &SourceConf{
		Name:   "",
		Source: "",
		Config: []byte(`foo`),
	}

	events := c.GetResponses(&Source{"flys", cnf}, "formfoo", "oldtoken", 350)
	e := Sliceit(events)

	fmt.Printf("terminamos la ecusion: %v\n", e)

	// connector.LoadEvents(c, "flys", "parent_surveyid")
}
