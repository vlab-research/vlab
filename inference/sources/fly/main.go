package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/caarlos0/env/v6"
	"github.com/dghubble/sling"
	"github.com/vlab-research/vlab/inference/connector"
	. "github.com/vlab-research/vlab/inference/inference-data"
)

func handle(err error) {
	if err != nil {
		log.Fatal(err)
	}
}

type GetResponsesParams struct {
	PageSize int    `url:"pageSize"`
	After    string `url:"after,omitempty"`
	Survey   string `url:"survey"`
}

type FlyTime time.Time

func (t *FlyTime) UnmarshalJSON(b []byte) error {
	s := strings.Trim(string(b), "\"")

	parsed, err := time.ParseInLocation("2006-01-02 15:04:05-07:00", s, time.UTC)

	if err != nil {
		return err
	}

	*t = FlyTime(parsed)
	return nil
}

type GetResponsesResponse struct {
	Responses []struct {
		ParentSurveyID     string                     `json:"parent_surveyid"`
		Token              string                     `json:"token"`
		ParentShortcode    string                     `json:"parent_shortcode"`
		Shortcode          string                     `json:"shortcode"`
		SurveyID           string                     `json:"surveyid"`
		FlowID             string                     `json:"flowid"`
		UserID             string                     `json:"userid"`
		QuestionRef        string                     `json:"question_ref"`
		QuestionIdx        string                     `json:"question_idx"`
		QuestionText       string                     `json:"question_text"`
		Response           string                     `json:"response"`
		Timestamp          FlyTime                    `json:"timestamp"`
		Metadata           map[string]json.RawMessage `json:"Metadata"`
		Pageid             string                     `json:"pageid"`
		TranslatedResponse string                     `json:"translated_response"`
	} `json:"responses"`
}

type Answer struct {
	Response           string `json:"response"`
	TranslatedResponse string `json:"translated_response"`
	SurveyID           string `json:"survey_id"`
	Shortcode          string `json:"shortcode"`
}

type FlyConnector struct {
	BaseUrl  string `env:"FLY_BASE_URL,required"`
	PageSize int    `env:"FLY_PAGE_SIZE,required"`
}

type FlyError struct {
	Code string `json:"code"`
}

func (e *FlyError) Empty() bool {
	return e.Code == ""
}

func (e *FlyError) Error() string {
	return e.Code
}

func (c *FlyConnector) loadEnv() {
	err := env.Parse(c)
	handle(err)
}

func Call(client *http.Client, baseUrl string, key string, params *GetResponsesParams) (*GetResponsesResponse, error) {

	fmt.Printf("Making call to: %s", baseUrl)

	sli := sling.New().Client(client).Base(baseUrl).Set("Accept", "application/json").Set("Authorization", fmt.Sprintf("Bearer %s", key))

	res := new(GetResponsesResponse)
	apiError := new(FlyError)

	_, err := sli.Get("responses").QueryStruct(params).Receive(res, apiError)

	if err != nil {
		return nil, err
	}

	if !apiError.Empty() {
		return nil, apiError
	}
	return res, nil
}

type FlyCredentials struct {
	APIKey string `json:"api_key"`
}

type FlyConfig struct {
	SurveyName string `json:"survey_name"`
}

func GetCredentials(source *Source) (*FlyCredentials, error) {
	details := source.Credentials.Details
	creds := new(FlyCredentials)
	err := json.Unmarshal(details, creds)
	return creds, err
}

func GetConfig(source *Source) (*FlyConfig, error) {
	b := source.Conf.Config
	conf := new(FlyConfig)
	err := json.Unmarshal(b, conf)
	return conf, err
}

func (c FlyConnector) GetResponses(source *Source, token string, idx int) <-chan *InferenceDataEvent {

	fmt.Printf("Getting responses for: %s", source.StudyID)

	events := make(chan *InferenceDataEvent)

	conf, err := GetConfig(source)
	if err != nil {
		handle(err)
	}

	params := &GetResponsesParams{PageSize: c.PageSize, After: token, Survey: conf.SurveyName}
	client := &http.Client{}

	creds, err := GetCredentials(source)
	if err != nil {
		handle(err)
	}

	go func() {
		defer close(events)
		params.After = token

		for {
			res, err := Call(client, c.BaseUrl, creds.APIKey, params)

			if err != nil {
				handle(err)
			}
			for _, item := range res.Responses {

				params.After = item.Token

				// NOTE: putting shortcode/surveyid as value is a bit
				// funky, one could imagine it as part of Variable...
				p := Answer{
					Response:           item.Response,
					TranslatedResponse: item.TranslatedResponse,
					SurveyID:           item.SurveyID,
					Shortcode:          item.Shortcode,
				}

				dat, err := json.Marshal(p)
				if err != nil {
					log.Fatal(err)
				}

				idx++
				event := &InferenceDataEvent{
					User:       User{ID: item.UserID, Metadata: item.Metadata},
					Study:      source.StudyID,
					SourceConf: source.Conf,
					Timestamp:  time.Time(item.Timestamp),
					Idx:        idx,
					Pagination: item.Token,
					Variable:   item.QuestionRef,
					Value:      []byte(dat),
				}
				events <- event
			}

			if len(res.Responses) < params.PageSize {
				break
			}

		}
	}()

	return events
}

func (c FlyConnector) Handler(source *Source, lastEvent *InferenceDataEvent) <-chan *InferenceDataEvent {
	token := ""
	idx := 0

	if lastEvent != nil {
		token = lastEvent.Pagination
		idx = lastEvent.Idx
	}

	events := c.GetResponses(source, token, idx)
	return events
}

func main() {
	c := FlyConnector{}
	c.loadEnv()

	connector.LoadEvents(c, "fly", "idx")
}
