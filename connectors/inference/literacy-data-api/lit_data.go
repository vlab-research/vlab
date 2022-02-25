package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"time"

	"github.com/caarlos0/env/v6"
	"github.com/dghubble/sling"

	"github.com/vlab-research/vlab/connectors/inference/connector"
)

func handle(err error) {
	if err != nil {
		log.Fatal(err)
	}
}

type LitDataTimestamp struct {
	time.Time
}

func (t *LitDataTimestamp) UnmarshalJSON(b []byte) error {
	var i int64
	err := json.Unmarshal(b, &i)
	if err != nil {
		return err
	}
	*t = LitDataTimestamp{time.Unix(0, i*1000).UTC()}
	return nil
}

type LitDataEvent struct {
	AttributionURL json.RawMessage `json:"attribution_url" validate:"required"`
	AppID          string          `json:"app_id" validate:"required"`
	OrderedID      int64           `json:"ordered_id" validate:"required"`
	User           struct {
		ID            string                     `json:"id" validate:"required"`
		Metadata      map[string]json.RawMessage `json:"metadata" validate:"required"`
		AdAttribution struct {
			Source string `json:"source"`
			Data   struct {
				AdvertisingID string `json:"advertising_id"`
				// add other types of ids for other sources...
			} `json:"data"`
		} `json:"ad_attribution"`
	} `json:"user" validate:"required"`
	Event struct {
		Name      string           `json:"name"`
		Date      string           `json:"date"`
		Timestamp LitDataTimestamp `json:"timestamp"`
		ValueType string           `json:"value_type"`
		Value     string           `json:"value"`
		Level     string           `json:"level"`
		Profile   string           `json:"profile"`
		RawData   struct {
			Action string `json:"action"`
			Label  string `json:"label"`
			Value  struct {
				StringValue string  `json:"string_value"`
				IntValue    int64   `json:"int_value"`
				FloatValue  float32 `json:"float_value"`
				DoubleValue float64 `json:"double_value"`
			} `json:"value"`
		} `json:"rawData"`
	} `json:"event" validate:"required"`
}

func marshalValue(lde *LitDataEvent) json.RawMessage {

	v := LitDataValue{lde.Event.Value, lde.Event.ValueType, lde.Event.Level, lde.Event.Profile}
	b, err := json.Marshal(v)
	if err != nil {
		// shouldn't happen, just string/json.RawMessage
		panic(err)
	}

	return b
}

func (lde *LitDataEvent) AsInferenceDataEvent(source *connector.Source, idx int) *connector.InferenceDataEvent {

	md := map[string]json.RawMessage{}
	for k, v := range lde.User.Metadata {
		md[k] = v
	}
	md["attribution_url"] = lde.AttributionURL
	md["advertising_id"] = []byte(fmt.Sprintf(`"%s"`, lde.User.AdAttribution.Data.AdvertisingID))

	from := fmt.Sprintf("%d", lde.Event.Timestamp.Time.Unix())

	return &connector.InferenceDataEvent{
		User:       connector.User{lde.User.ID, md},
		Study:      source.StudyID,
		SourceConf: source.Conf,
		Timestamp:  lde.Event.Timestamp.Time,
		Variable:   lde.Event.Name,
		Value:      marshalValue(lde),
		Idx:        idx,
		Pagination: from,
	}
}

func (lde *LitDataEvent) Print() {
	b, err := json.Marshal(lde)
	if err != nil {
		panic(err)
	}

	fmt.Println(string(b))
}

type LitDataResponse struct {
	NextCursor string          `json:"nextCursor"`
	Data       []*LitDataEvent `json:"data"`
}

type LitDataAPIParams struct {
	From          int    `url:"from" json:"from,omitempty"`
	Token         string `url:"token,omitempty" json:"token,omitempty"`
	AppID         string `url:"app_id" json:"app_id"`
	AttributionID string `url:"attribution_id,omitempty" json:"attribution_id"`
}

type LitDataConfig struct {
	From          string `json:"from"`
	AppID         string `json:"app_id"`
	AttributionID string `json:"attribution_id"`
}

type LitDataError struct {
	Msg string `json:"msg"`
}

type LitDataValue struct {
	Value     string `json:"value"`
	ValueType string `json:"value_type"`
	Level     string `json:"level"` // TODO: make sure is always an int
	Profile   string `json:"profile"`
}

func (e *LitDataError) Empty() bool {
	return e.Msg == ""
}

func (e *LitDataError) AsError() error {
	if e.Empty() {
		return nil
	}
	return e
}

func (e *LitDataError) Error() string {
	return e.Msg
}

func Call(client *http.Client, baseUrl string, params *LitDataAPIParams) (*LitDataResponse, error) {
	sli := sling.New().Client(client).Base(baseUrl).Set("Accept", "application/json")

	res := new(LitDataResponse)
	apiError := new(LitDataError)
	_, err := sli.Get("fetch_latest").QueryStruct(params).Receive(res, apiError)

	if err != nil {
		return nil, err
	}

	if !apiError.Empty() {
		return nil, apiError.AsError()
	}

	return res, nil
}

func GetEvents(source *connector.Source, url string, params *LitDataAPIParams, i int) <-chan *connector.InferenceDataEvent {
	client := http.DefaultClient
	events := make(chan *connector.InferenceDataEvent)

	go func() {
		defer close(events)

		for {
			response, err := Call(client, url, params)
			if err != nil {
				panic(err)
			}

			for _, r := range response.Data {
				i++
				if i%10000 == 0 {
					log.Println(fmt.Sprintf("Collected %d results.", i))
				}

				events <- r.AsInferenceDataEvent(source, i)
			}

			params.Token = response.NextCursor
			if params.Token == "" {
				break
			}
		}
	}()

	return events
}

type LitDataApiConnector struct {
	LitDataUrl string `env:"LITERACY_DATA_API_URL,required"`
}

func (c *LitDataApiConnector) loadEnv() *LitDataApiConnector {
	err := env.Parse(c)
	handle(err)
	return c
}

func (c LitDataApiConnector) Handler(source *Source, lastEvent *InferenceDataEvent) <-chan *InferenceDataEvent {
	litDataConfig := new(LitDataConfig)
	err := json.Unmarshal(source.Conf.Config, litDataConfig)
	handle(err)

	log.Println("Literacy Data Connector getting data for: ", litDataConfig)

	from, err := strconv.Atoi(litDataConfig.From)
	handle(err)

	idx := 0

	if lastEvent != nil {
		from, err = strconv.Atoi(lastEvent.Pagination)
		handle(err) // shouldn't happen

		idx = lastEvent.Idx
	}

	// NOTE: right now the config is the params, but that will change
	params := &LitDataAPIParams{
		from,
		"", // no token
		litDataConfig.AppID,
		litDataConfig.AttributionID,
	}

	events := GetEvents(source, c.LitDataUrl, params, idx)
	return events
}

func main() {
	c := &LitDataApiConnector{}
	c = c.loadEnv()
	LoadEvents(c, "literacy_data_api", "timestamp")
}
