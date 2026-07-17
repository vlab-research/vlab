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

func GetEvents(pool *pgxpool.Pool, study string) ([]*InferenceDataEvent, error) {
	events := []*InferenceDataEvent{}

	query := `
        SELECT data
        FROM inference_data_events
        WHERE study_id = $1
        `

	rows, err := pool.Query(context.Background(), query, study)
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

	query := `SELECT id
	          FROM study_state
	          WHERE start_date < NOW()
	          AND end_date > NOW() - INTERVAL '7 days'`
	rows, err := pool.Query(context.Background(), query)

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

// swooshStudy processes a single study. It returns an error instead of
// fataling so that one misconfigured study cannot abort the whole run.
// (Mirrors connector.collectEventsForStudy — see inference/connector/connector.go.)
func swooshStudy(pool *pgxpool.Pool, study string) error {
	log.Printf("Swooshing %s\n", study)

	events, err := GetEvents(pool, study)
	if err != nil {
		return fmt.Errorf("study %s: reading events: %w", study, err)
	}
	log.Printf("Swoosh read %d events.\n", len(events))

	mapping, err := GetInferenceDataConf(pool, study)
	if err != nil {
		// No inference_data conf → nothing to aggregate. Not an error; skip.
		log.Printf("Could not get inference_data conf for study %s; skipping\n", study)
		return nil
	}

	id, extractionErrors, err := Reduce(events, mapping)
	if err != nil {
		return fmt.Errorf("study %s: reduce: %w", study, err)
	}

	// TODO(study-errors-surfacing): persist these to study_errors so the user sees them.
	log.Printf("Swoosh had %d extractionErrors\n", len(extractionErrors))
	for _, e := range extractionErrors {
		log.Println(e)
	}

	log.Printf("Swoosh storing InferenceData from %d users\n", len(id))
	if err := WriteInferenceData(pool, study, id); err != nil {
		return fmt.Errorf("study %s: writing inference data: %w", study, err)
	}
	return nil
}

func main() {
	cnf := getConfig()
	pool, err := pgxpool.Connect(context.Background(), cnf.DB)
	handle(err) // connection failure is still fatal — nothing can run

	studies, err := GetActiveStudies(pool)
	handle(err) // can't get the work list → fatal

	log.Printf("Swooshing %d studies\n", len(studies))

	failed := 0
	for _, study := range studies {
		if err := swooshStudy(pool, study); err != nil {
			log.Printf("ERROR %v", err)
			failed++
			continue
		}
	}
	log.Printf("Swoosh done. %d/%d studies failed.\n", failed, len(studies))
}
