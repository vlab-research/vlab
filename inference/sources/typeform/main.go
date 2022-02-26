package main

import (
	"encoding/json"
	"log"

	"github.com/caarlos0/env/v6"
)

func handle(err error) {
	if err != nil {
		log.Fatal(err)
	}
}

type TypeformConfig struct {
	From string `json:"from"` // ??????????
}

type GetResponsesParams struct {
}

type TypeformConnector struct {
	TypeformBaseUrl string `env:"TYPEFORM_BASE_URL,required"`
}

func (c TypeformConnector) loadEnv() TypeformConnector {
	err := env.Parse(&c)
	handle(err)
	return c
}

func GetResponses(source *Source, url string, params *GetResponsesParams, i int) <-chan *InferenceDataEvent {

	// get typeform responses

	// get pagination token

	// mutate params to keep trackof latetst pagination token
	// params.Token = response.NextCursor

	// convert each response to an InferenceDataEvent

}

func (c TypeformConnector) Handler(source *Source, lastEvent *InferenceDataEvent) <-chan *InferenceDataEvent {
	typeformConfig := new(TypeformConfig)
	err := json.Unmarshal(source.Conf.Config, typeformConfig)
	handle(err)

	log.Println("Literacy Data Connector getting data for: ", typeformConfig)

	// from, err := strconv.Atoi(typeformConfig.From)
	// handle(err)

	// if lastEvent != nil {
	// 	from, err = strconv.Atoi(lastEvent.Pagination)
	// 	handle(err) // shouldn't happen
	// }

	params := &GetResponsesParams{}
	events := GetResponses(source, c.TypeformBaseUrl, params, lastEvent.Idx)

	return events
}

func main() {
	c := TypeformConnector{}
	c.loadEnv()
	LoadEvents(c, "typeform", "idx")
}
