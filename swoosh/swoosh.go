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

func GetInferenceDataConf(pool *pgxpool.Pool, study string) (*InferenceDataConf, error) {
	q := `
        SELECT conf
        FROM study_confs
        WHERE study_id = $1
        AND conf_type = 'inference_data'
        ORDER BY created DESC
        LIMIT 1;
        `

	conf := new(InferenceDataConf)
	err := pool.QueryRow(context.Background(), q, study).Scan(conf)
	if err != nil {
		return nil, err
	}

	return conf, nil
}

func main() {
	cnf := getConfig()
	pool, err := pgxpool.Connect(context.Background(), cnf.DB)
	handle(err)

	// This part should go in the "literacy data connector"
	sources, err := GetStudyConfs(pool, "literacy_data_api")
	handle(err)

	for _, source := range sources {
		// --------------------------
		// This part should go in the "literacy data connector"
		// --------------------------

		// create config -- env vars, not study-specific stuff....
		url := "http://localhost:4000"
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

		events := GetEvents(source.StudyID, url, params)
		log.Println(fmt.Printf("Swoosh read %d events.", len(events)))

		// ---------------------
		// write to Kafka here.
		// ---------------------

		// ---------------------
		// this part goes in Swoosh. Is study-specific, picking the variables based on
		// and the source. It gets the events from the event store in batch
                // mode or from kafka in streaming mode.
		// ---------------------
		mapping, err := GetInferenceDataConf(pool, source.StudyID)
		handle(err)
		id, err := Reduce(events, mapping)
		handle(err)

		log.Println(fmt.Printf("Swoosh storing InferenceData from %d users", len(id)))
		err = WriteInferenceData(pool, source.StudyID, id)
		handle(err)

	}

}
