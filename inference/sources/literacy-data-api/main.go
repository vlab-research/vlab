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
	"github.com/vlab-research/vlab/inference/connector"
	. "github.com/vlab-research/vlab/inference/inference-data"
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
	*t = LitDataTimestamp{time.Unix(0, i/1000000).UTC()}
	return nil
}

type LitDataEventParams struct {
	Label string `json:"label"`
	Value struct {
		StringValue interface{} `json:"string_value"`
		IntValue    string      `json:"int_value"`
		FloatValue  interface{} `json:"float_value"`
		DoubleValue interface{} `json:"double_value"`
	} `json:"value"`
	Action string `json:"action"`
}

type LitDataEvent struct {
	UserPseudoID   string           `json:"user_pseudo_id"`
	EventName      string           `json:"event_name"`
	EventTimestamp LitDataTimestamp `json:"event_timestamp"`
	TrafficSource  struct {
		Name   string      `json:"name"`
		Medium interface{} `json:"medium"`
		Source string      `json:"source"`
	} `json:"traffic_source"`
	Device struct {
		Category               string      `json:"category"`
		MobileBrandName        string      `json:"mobile_brand_name"`
		MobileModelName        string      `json:"mobile_model_name"`
		MobileMarketingName    string      `json:"mobile_marketing_name"`
		MobileOsHardwareModel  string      `json:"mobile_os_hardware_model"`
		OperatingSystem        string      `json:"operating_system"`
		OperatingSystemVersion string      `json:"operating_system_version"`
		VendorID               interface{} `json:"vendor_id"`
		AdvertisingID          interface{} `json:"advertising_id"`
		Language               string      `json:"language"`
		IsLimitedAdTracking    string      `json:"is_limited_ad_tracking"`
		TimeZoneOffsetSeconds  string      `json:"time_zone_offset_seconds"`
		Browser                interface{} `json:"browser"`
		BrowserVersion         interface{} `json:"browser_version"`
		WebInfo                interface{} `json:"web_info"`
	} `json:"device"`
	Geo struct {
		Continent    string `json:"continent"`
		Country      string `json:"country"`
		Region       string `json:"region"`
		City         string `json:"city"`
		SubContinent string `json:"sub_continent"`
		Metro        string `json:"metro"`
	} `json:"geo"`
	EventParams LitDataEventParams `json:"event_params"`
}

func marshalValue(lde *LitDataEvent) json.RawMessage {
	v := lde.EventParams
	b, err := json.Marshal(v)
	if err != nil {
		// shouldn't happen, just string/json.RawMessage
		panic(err)
	}
	return b
}

func marshalMetadata(el interface{}) map[string]json.RawMessage {
	b, err := json.Marshal(el)
	handle(err) // shouldn't happen

	md := new(map[string]json.RawMessage)
	err = json.Unmarshal(b, md)
	handle(err)

	return *md
}

func (lde *LitDataEvent) AsInferenceDataEvent(source *Source, idx int) *InferenceDataEvent {

	md := map[string]json.RawMessage{}
	for k, v := range marshalMetadata(lde.Geo) {
		md[k] = v
	}
	for k, v := range marshalMetadata(lde.Device) {
		md[k] = v
	}

	// shouldn't error
	md["traffice_source"], _ = json.Marshal(lde.TrafficSource.Source)

	from := fmt.Sprintf("%d", lde.EventTimestamp.Time.Unix())
	variable := lde.EventName + "_" + lde.EventParams.Action

	return &InferenceDataEvent{
		User:       User{ID: lde.UserPseudoID, Metadata: md},
		Study:      source.StudyID,
		SourceConf: source.Conf,
		Timestamp:  lde.EventTimestamp.Time,
		Variable:   variable,
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
	AppID         string `url:"app_id" json:"app_id"`
	TrafficSource string `url:"traffic_source" json:"traffic_source"`
	Limit         int    `url:"limit" json:"limit,omitempty"`
	Country       string `url:"country,omitempty" json:"country"`
}

type LitDataConfig struct {
	From          string `json:"from"`
	AppID         string `json:"app_id"`
	TrafficSource string `url:"traffic_source" json:"traffic_source"`
	Country       string `url:"country,omitempty" json:"country"`
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

func GetEvents(source *Source, url string, params *LitDataAPIParams, i int) <-chan *InferenceDataEvent {
	client := http.DefaultClient
	events := make(chan *InferenceDataEvent)

	go func() {
		defer close(events)

		for {
			response, err := Call(client, url, params)
			if err != nil {
				panic(err)
			}

			for _, r := range response.Data {
				i++
				if i%1000 == 0 {
					log.Println(fmt.Sprintf("Collected %d results.", i))
				}

				// For pagination
				params.From = int(r.EventTimestamp.Time.Unix())

				// push event
				events <- r.AsInferenceDataEvent(source, i)
			}

			if len(response.Data) < params.Limit {
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

	// Note: thin abstraction layer...
	params := &LitDataAPIParams{
		From:          from,
		AppID:         litDataConfig.AppID,
		Country:       litDataConfig.Country,
		TrafficSource: litDataConfig.TrafficSource,
		Limit:         1000,
	}

	events := GetEvents(source, c.LitDataUrl, params, idx)
	return events
}

func main() {
	c := &LitDataApiConnector{}
	c = c.loadEnv()
	connector.LoadEvents(c, "literacy_data_api", "timestamp")
}
