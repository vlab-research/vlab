package main

import (
	"context"
	"fmt"
	"log"

	"github.com/caarlos0/env/v6"
	"github.com/jackc/pgx/v4/pgxpool"

	. "github.com/vlab-research/vlab/inference/inference-data"
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
        SELECT conf->0
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

func GetEvents(pool *pgxpool.Pool, study string) ([]*InferenceDataEvent, error) {
	events := []*InferenceDataEvent{}
	rows, err := pool.Query(context.Background(), "SELECT data from inference_data_events where study_id = $1", study)
	if err != nil {
		return events, err
	}

	for rows.Next() {
		event := new(InferenceDataEvent)
		err := rows.Scan(event)
		if err != nil {
			return events, err
		}

		events = append(events, event)
	}

	return events, nil
}

func GetActiveStudies(pool *pgxpool.Pool) ([]string, error) {
	studies := []string{}

	// TODO: get only active!
	rows, err := pool.Query(context.Background(), "SELECT id from studies")
	if err != nil {
		return studies, err
	}

	for rows.Next() {
		var study string
		err := rows.Scan(&study)
		if err != nil {
			return studies, err
		}
		studies = append(studies, study)
	}

	return studies, nil
}

func main() {
	cnf := getConfig()
	pool, err := pgxpool.Connect(context.Background(), cnf.DB)
	handle(err)

	studies, err := GetActiveStudies(pool)
	handle(err)

	for _, study := range studies {
		events, err := GetEvents(pool, study)
		handle(err)
		log.Println(fmt.Printf("Swoosh read %d events.", len(events)))

		mapping, err := GetInferenceDataConf(pool, study)
		handle(err)
		id, err := Reduce(events, mapping)
		handle(err)

		log.Println(fmt.Printf("Swoosh storing InferenceData from %d users", len(id)))
		err = WriteInferenceData(pool, study, id)
		handle(err)

	}

}
