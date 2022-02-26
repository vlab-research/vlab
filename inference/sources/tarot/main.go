package main

import (
	"context"
	"encoding/json"
	"log"

	"github.com/caarlos0/env/v6"
	"github.com/jackc/pgx/v4/pgxpool"
	"github.com/vlab-research/vlab/inference/connector"
	. "github.com/vlab-research/vlab/inference/inference-data"
)

var (
	pool = new(pgxpool.Pool)
)

func handle(err error) {
	if err != nil {
		log.Fatal(err)
	}
}

// Assume it's already created in Tarot? Or no?? First attempt creates if gets 404?
// but how to get ID then???
type TarotConfig struct {
	// Strategy              string `json:"strategy"`
	// TarotConfig           string `json:""`
	InferenceVariableName string `json:"inference_data_name"`
	TarotStudyID          string `json:"tarot_study_id"`
}

type TreatmentAssignmentRequest struct {
	UserId     string          `json:"user_id"`
	Covariates json.RawMessage `json:"covariates,omitempty"`
}

type TreatmentAssignmentParams []*TreatmentAssignmentRequest

type TarotConnector struct {
	DB       string `env:"PG_URL,required"` // postgres://user:password@host:port/db
	TarotUrl string `env:"TAROT_URL,required"`
	pool     *pgxpool.Pool
}

func (c TarotConnector) loadEnv() TarotConnector {
	err := env.Parse(&c)
	handle(err)

	pool, err := pgxpool.Connect(context.Background(), c.DB)
	handle(err)

	c.pool = pool
	return c
}

func GetNewAssignments(source *Source, url string, params TreatmentAssignmentParams) <-chan *InferenceDataEvent {

	// get typeform responses

	// get pagination token

	// mutate params to keep trackof latetst pagination token
	// params.Token = response.NextCursor

	// convert each response to an InferenceDataEvent

}

func (c TarotConnector) Handler(source *Source, lastEvent *InferenceDataEvent) <-chan *InferenceDataEvent {
	tarotConfig := new(TarotConfig)
	err := json.Unmarshal(source.Conf.Config, tarotConfig)
	handle(err)

	log.Println("Tarot getting data for: ", tarotConfig)

	params := GetUsersMissingAssignments(c.pool, tarotConfig)
	events := GetNewAssignments(source, c.TarotUrl, params)
	return events
}

func main() {
	c := TarotConnector{}
	c.loadEnv()
	connector.LoadEvents(c, "tarot", "idx")
}
