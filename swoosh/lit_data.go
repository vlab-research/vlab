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
		lde.User.Event.Timestamp.Time,
		lde.User.Event.Action,
		lde.User.Event.ValueType,
		lde.User.Event.Value,
		nil,
	}
}

type LitDataResponse struct {
	NextCursor string          `json:"nextCursor"`
	Data       []*LitDataEvent `json:"data"`
}

type LitDataParams struct {
	From          string `url:"from"`
	AppID         string `url:"app_id"`
	AttributionID string `url:"attribution_id,omitempty"`
}

type LitDataError struct {
	Msg string `json:"msg"`
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

func Wrapper(client *http.Client, cursor string) (*LitDataResponse, error) {
	baseUrl := "http://localhost:4000"
	sli := sling.New().Client(client).Base(baseUrl).Set("Accept", "application/json")

	params := &LitDataParams{cursor, "com.eduapp4syria.feedthemonsterBangla", "FB_Bangla_App_6_2021"}

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

// TODO: cleanup temp helper for developing off lit data api
func printJSON(data *LitDataEvent) {
	b, err := json.Marshal(data)
	if err != nil {
		panic(err)
	}

	fmt.Println(string(b))
}

func Iterate(client *http.Client) []*InferenceDataEvent {
	cursor := "0"
	results := []*LitDataEvent{}
	i := 0

	for {
		i++
		if cursor == "" {
			break
		}
		res, err := Wrapper(client, cursor)
		if err != nil {
			fmt.Println(err)
			return nil
		}

		results = append(results, res.Data...)
		cursor = res.NextCursor

		if i%10 == 0 {
			log.Println(fmt.Sprintf("Collected %d results.", len(results)))
		}
	}

	events := []*InferenceDataEvent{}

	for _, res := range results {
		events = append(events, res.AsInferenceDataEvent("foo"))
	}

	return events
}
