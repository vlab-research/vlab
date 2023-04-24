package main

import (
	"encoding/json"
	"fmt"
	"github.com/caarlos0/env/v6"
	"github.com/dghubble/sling"
	"github.com/tidwall/gjson"
	"github.com/tidwall/sjson"
	"github.com/vlab-research/vlab/inference/connector"
	. "github.com/vlab-research/vlab/inference/inference-data"
	"log"
	"net/http"
	"net/url"
	"time"
)

func handle(err error) {
	if err != nil {
		log.Fatal(err)
	}
}

type AlchemerConnector struct {
	BaseUrl  string `env:"ALCHEMER_BASE_URL,required"`
	PageSize int    `env:"ALCHEMER_PAGE_SIZE,required"`
}

// TODO: add validation!
type AlchemerConfig struct {
	// Timezone in the format of:
	// https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
	TimeZone string `json:"timezone"`
	SurveyID int    `json:"survey_id"`
}

type Filter struct {
	Field    string
	Operator string
	Value    string
}

type GetResponsesParams struct {
	ApiToken       string `url:"api_token"`
	ApiTokenSecret string `url:"api_token_secret"`
	Page           int    `url:"page",omitempty`
	ResultsPerPage int    `url:"resultsperpage,omitempty"`
}

type URLVariable struct {
	Key   string `json:"key"`
	Value string `json:"value"`
	Type  string `json:"type"`
}

type URLVariables map[string]URLVariable

func (v *URLVariables) UnmarshalJSON(b []byte) error {
	var vv map[string]URLVariable
	e := json.Unmarshal(b, &vv)

	// Alchemer sends url_variables as an empty array when empty
	// this will then return an error when unmarshalling, and
	// we create an empty variables
	if e != nil {
		*v = URLVariables{}
		return nil
	}
	*v = vv
	return nil
}

type SurveyDatum struct {
	Options map[string]struct {
		ID             int    `json:"id"`
		Option         string `json:"option"`
		OriginalAnswer string `json:"original_answer"`
		Answer         string `json:"answer"`
	} `json:"options"`
	ID             int    `json:"id"`
	Type           string `json:"type"`
	Question       string `json:"question"`
	SectionID      int    `json:"section_id"`
	OriginalAnswer string `json:"original_answer"`
	Answer         string `json:"answer"`
	AnswerID       int    `json:"answer_id"`
	Shown          bool   `json:"shown"`
}

type GetResponsesResponse struct {
	ResultOk   bool `json:"result_ok"`
	TotalCount int  `json:"total_count"`
	Page       int  `json:"page"`
	TotalPages int  `json:"total_pages"`

	// can be string or int...
	// ResultsPerPage string  `json:"results_per_page"`
	Data []struct {
		ID            string                     `json:"id"`
		ContactID     string                     `json:"contact_id"`
		Status        string                     `json:"status"`
		IsTestData    string                     `json:"is_test_data"`
		DateSubmitted string                     `json:"date_submitted"`
		SessionID     string                     `json:"session_id"`
		Language      string                     `json:"language"`
		DateStarted   string                     `json:"date_started"`
		LinkID        string                     `json:"link_id"`
		URLVariables  URLVariables               `json:"url_variables,omitempty"`
		IPAddress     string                     `json:"ip_address"`
		Referer       string                     `json:"referer"`
		UserAgent     string                     `json:"user_agent"`
		ResponseTime  int                        `json:"response_time"`
		Longitude     string                     `json:"longitude"`
		Latitude      string                     `json:"latitude"`
		Country       string                     `json:"country"`
		City          string                     `json:"city"`
		Region        string                     `json:"region"`
		Postal        string                     `json:"postal"`
		Dma           string                     `json:"dma"`
		SurveyData    map[string]json.RawMessage `json:"survey_data,omitempty"`
	} `json:"data"`
}

type AlchemerError struct {
	ResultOk bool   `json:"result_ok"`
	Message  string `json:"message"`
	Code     string `json:"code"`
}

func (e *AlchemerError) Empty() bool {
	return e.Code == ""
}

func (e *AlchemerError) Error() string {
	return e.Message
}

func (c *AlchemerConnector) loadEnv() *AlchemerConnector {
	err := env.Parse(c)
	handle(err)
	return c
}

type AlchemerCreds struct {
	ApiToken       string `json:"api_token"`
	ApiTokenSecret string `json:"api_token_secret"`
}

func parseTimestamp(config *AlchemerConfig, s string) (*time.Time, error) {
	loc, e := time.LoadLocation(config.TimeZone)
	if e != nil {
		return nil, e
	}
	ti, e := time.ParseInLocation("2006-01-02 15:04:05 MST", s, loc)

	if e != nil {
		return nil, e
	}

	return &ti, nil
}

func makeFilterQuery(filters []Filter) url.Values {
	v := url.Values{}

	for i, f := range filters {
		v.Add(fmt.Sprintf("filter[field][%d]", i), f.Field)
		v.Add(fmt.Sprintf("filter[operator][%d]", i), f.Operator)
		v.Add(fmt.Sprintf("filter[value][%d]", i), f.Value)
	}

	return v
}

func parseCreds(b json.RawMessage) *AlchemerCreds {
	creds := new(AlchemerCreds)
	err := json.Unmarshal(b, creds)
	handle(err)
	return creds
}

func Call(client *http.Client, baseUrl string, survey int, params *GetResponsesParams, token string) (*GetResponsesResponse, error) {

	// TODO: move out of here and into TypeformConnector
	sli := sling.New().Client(client).Base(baseUrl).Set("Accept", "application/json")

	filters := []Filter{
		{"status", "=", "Complete"},
	}

	if token != "" {
		filters = append(filters, Filter{"date_submitted", ">", token})
	}

	filterQuery := makeFilterQuery(filters).Encode()

	res := new(GetResponsesResponse)
	apiError := new(AlchemerError)

	_, err := sli.New().Get(fmt.Sprintf("/survey/%d/surveyresponse?%s", survey, filterQuery)).QueryStruct(params).Receive(res, apiError)

	if err != nil {
		return nil, err
	}

	if !apiError.Empty() {
		return nil, apiError
	}

	return res, nil
}

func (c AlchemerConnector) GetResponses(source *Source, config *AlchemerConfig, token string, idx int) <-chan *InferenceDataEvent {
	events := make(chan *InferenceDataEvent)

	creds := parseCreds(source.Credentials.Details)
	params := &GetResponsesParams{
		ResultsPerPage: c.PageSize,
		ApiToken:       creds.ApiToken,
		ApiTokenSecret: creds.ApiTokenSecret,
	}

	client := &http.Client{}

	go func() {
		defer close(events)

		for {
			res, err := Call(client, c.BaseUrl, config.SurveyID, params, token)

			if err != nil {
				handle(err)
			}

			if res.TotalCount == 0 {
				break
			}

			for _, item := range res.Data {

				// for next round of pagination
				// TODO: are responses guaranteed to be ordered
				// by date submitted? If not, this doesn't work.
				token = item.DateSubmitted

				b, _ := json.Marshal(item)
				toDelete := []string{"url_variables", "survey_data", "date_submitted"}
				for _, v := range toDelete {
					b, err = sjson.DeleteBytes(b, v)
					handle(err)
				}

				var md map[string]json.RawMessage
				err := json.Unmarshal(b, &md)
				handle(err)

				user := User{ID: item.ID, Metadata: md}

				timestamp, err := parseTimestamp(config, item.DateSubmitted)
				handle(err)

				for _, value := range item.URLVariables {
					idx++

					event := &InferenceDataEvent{
						User:       user,
						Study:      source.StudyID,
						SourceConf: source.Conf,
						Timestamp:  *timestamp,
						Variable:   value.Key,
						Value:      []byte(value.Value), // should we take more?
						Idx:        idx,
						Pagination: item.DateSubmitted,
					}
					events <- event

				}

				for key, d := range item.SurveyData {
					idx++

					// NOTE: the raw json might be funky for
					// options and other answer types, need to see
					// if it's at all usable or not.
					filteredAnswer, err := sjson.DeleteBytes(d, "question")
					handle(err)

					// TODO: "shown" only seems to be true if the
					// question was answered. Confirm this is really
					// the case and, if not, improve.
					if gjson.Get(string(d), "shown").Bool() == false {
						continue
					}

					event := &InferenceDataEvent{
						User:       user,
						Study:      source.StudyID,
						SourceConf: source.Conf,
						Timestamp:  *timestamp,
						Variable:   key,
						Value:      filteredAnswer,
						Idx:        idx,
						Pagination: item.DateSubmitted,
					}
					events <- event
				}
			}
		}
	}()

	return events
}

func (c AlchemerConnector) Handler(source *Source, lastEvent *InferenceDataEvent) <-chan *InferenceDataEvent {
	config := new(AlchemerConfig)
	err := json.Unmarshal(source.Conf.Config, config)
	handle(err)

	log.Println("Alchemer connector getting data for: ", config)

	token := ""
	idx := 0

	if lastEvent != nil {
		token = lastEvent.Pagination
		idx = lastEvent.Idx
	}

	events := c.GetResponses(source, config, token, idx)
	return events
}

func main() {
	c := AlchemerConnector{}
	c.loadEnv()
	connector.LoadEvents(c, "alchemer", "idx")
}
