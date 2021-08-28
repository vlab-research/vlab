package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	"github.com/dghubble/sling"
)

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
	AttributionURL json.RawMessage `json:"attribution_url"`
	AppID          string          `json:"app_id"`
	OrderedID      int64           `json:"ordered_id"`
	User           struct {
		ID            string                     `json:"id"`
		Metadata      map[string]json.RawMessage `json:"metadata"`
		AdAttribution struct {
			Source string `json:"source"`
			Data   struct {
				AdvertisingID string `json:"advertising_id"`
				// add other types of ids for other sources...
			} `json:"data"`
		} `json:"ad_attribution"`
		Event struct {
			Name      string           `json:"name"`
			Date      string           `json:"date"`
			Timestamp LitDataTimestamp `json:"timestamp"`
			Label     string           `json:"label"`
			Action    string           `json:"action"`
			Value     json.RawMessage  `json:"value"`
			ValueType string           `json:"value_type"`
		} `json:"event"`
	} `json:"user"`
}

func marshalValue(lde *LitDataEvent) json.RawMessage {
	v := LitDataValue{lde.User.Event.Value, lde.User.Event.ValueType}
	b, err := json.Marshal(v)
	if err != nil {
		// shouldn't happen, just string/json.RawMessage
		panic(err)
	}

	return b
}

func (lde *LitDataEvent) AsInferenceDataEvent(study string) *InferenceDataEvent {

	md := map[string]json.RawMessage{}
	for k, v := range lde.User.Metadata {
		md[k] = v
	}
	md["attribution_url"] = lde.AttributionURL
	md["advertising_id"] = []byte(fmt.Sprintf(`"%s"`, lde.User.AdAttribution.Data.AdvertisingID))

	return &InferenceDataEvent{
		User{lde.User.ID, md},
		study,
		"literacy_data_api",
		lde.User.Event.Timestamp.Time,
		lde.User.Event.Action,
		marshalValue(lde),
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
	From          string `url:"from" json:"from"`
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
	Value     json.RawMessage `json:"value"`
	ValueType string          `json:"value_type"`
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

func GetEvents(study, url string, params *LitDataAPIParams) []*InferenceDataEvent {
	client := http.DefaultClient
	results := []*LitDataEvent{}
	i := 0

	for {
		i++
		if params.From == "" {
			break
		}

		res, err := Call(client, url, params)
		if err != nil {
			log.Fatal(err)
			return nil
		}

		results = append(results, res.Data...)
		params.From = res.NextCursor

		if i%10 == 0 {
			log.Println(fmt.Sprintf("Collected %d results.", len(results)))
		}
	}

	events := []*InferenceDataEvent{}

	for _, res := range results {
		ev := res.AsInferenceDataEvent(study)
		events = append(events, ev)
	}

	return events
}
