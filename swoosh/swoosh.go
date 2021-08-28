package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"

	"github.com/caarlos0/env/v6"
	"github.com/jackc/pgx/v4/pgxpool"
)

func handle(err error) {
	if err != nil {
		log.Fatal(err)
	}
}

type Config struct {
	DB string `env:"PG_URL,required"` // postgres://user:password@host:port/db
	// KafkaBrokers     string        `env:"KAFKA_BROKERS,required"`
	// KafkaPollTimeout time.Duration `env:"KAFKA_POLL_TIMEOUT,required"`
	// Topic            string        `env:"KAFKA_TOPIC,required"`
	// Group            string        `env:"KAFKA_GROUP,required"`
}

func getConfig() Config {
	cfg := Config{}
	err := env.Parse(&cfg)
	handle(err)
	return cfg
}

func main() {
	cnf := getConfig()
	pool, err := pgxpool.Connect(context.Background(), cnf.DB)
	handle(err)

	// create config -- env vars, not study-specific stuff....
	url := "http://localhost:4000"

	sources, err := GetStudyConfs(pool, "literacy_data_api")
	handle(err)

	for _, source := range sources {

		litDataConfig := new(LitDataConfig)
		err := json.Unmarshal(source.Conf.Config, litDataConfig)
		handle(err)

		log.Println("Swoosh getting data for: ", litDataConfig)

		// NOTE: right now the config is the params, but that will change
		params := &LitDataAPIParams{
			litDataConfig.From,
			litDataConfig.AppID,
			litDataConfig.AttributionID,
		}

		res := GetEvents(source.StudyID, url, params)
		log.Println(fmt.Printf("Swoosh read %d events.", len(res)))

		// ------------
		// write to Kafka
		// ------------

		// this part should now be study-specific, picking the variables based on
		// the config and the source. It consumes from kafka.

		mapping := &InferenceDataConf{map[string]*InferenceDataSource{
			"literacy_data_api": {
				VariableExtractionMapping: map[string]*ExtractionConf{
					// look at variable names
					"LevelSuccess_2": {Name: "level_2", Type: "existence", Function: "select", Params: []byte(`{"path": "value"}`)},
					"LevelSuccess_5": {Name: "level_5", Type: "existence", Function: "select", Params: []byte(`{"path": "value"}`)},
				},
				MetadataExtractionMapping: nil,
			},
		}}
		id, err := Reduce(res, mapping)
		handle(err)

		log.Println(fmt.Printf("Swoosh storing InferenceData from %d users", len(id)))

		err = WriteInferenceData(pool, source.StudyID, id)
		handle(err)

	}

}
