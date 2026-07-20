package main

import (
	"context"
	"fmt"
	"log"

	"github.com/caarlos0/env/v6"
	"github.com/google/uuid"
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

// GetEvents loads a study's events, restricted to sources that are still in the
// study's current inference_data conf (passed as `sources`). Events tagged with a
// source the owner has removed from the config are ignored at the read boundary —
// we reconcile the derived view to the config, we do not delete the underlying
// facts. See swooshStudy for the full rationale. source_name is part of the
// primary key, so the filter is a cheap residual on the per-study scan.
func GetEvents(pool *pgxpool.Pool, study string, sources []string) ([]*InferenceDataEvent, error) {
	events := []*InferenceDataEvent{}

	query := `
        SELECT data
        FROM inference_data_events
        WHERE study_id = $1
        AND source_name = ANY($2)
        `

	rows, err := pool.Query(context.Background(), query, study, sources)
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
//
// Every invocation emits immutable facts to study_run_events (run_started,
// then run_ok / run_error / extraction_*): "current errors" is a derived view
// over that log, which is how a broken study becomes visible in the dashboard.
// Event writes are best-effort and never affect the returned error.
func swooshStudy(pool *pgxpool.Pool, study string) error {
	log.Printf("Swooshing %s\n", study)

	runID := uuid.NewString()
	RecordEvent(pool, study, sourceInference, runID, eventRunStarted, "", "", "", nil)

	// Load the conf before the events: the conf's source list is what we filter
	// events by, and if there is no conf there is nothing to read.
	mapping, err := GetInferenceDataConf(pool, study)
	if err != nil {
		// No inference_data conf → nothing to aggregate. Not an error; skip.
		// A skip is a healthy outcome — it closes any prior run_error for this study.
		log.Printf("Could not get inference_data conf for study %s; skipping\n", study)
		recordRunOutcome(pool, study, runID, eventRunOK, "", "", "")
		return nil
	}

	// Reconcile the derived view to the current config: only process events whose
	// source is still in the latest inference_data conf. The config is the
	// authority on which sources a study cares about. When an owner deletes a data
	// source (e.g. OWIS Nigeria's single "Fly" source was split into "Fly HPV
	// Double" / "Fly HPV Triple" on 2026-07-13), its historical events are
	// orphaned. We ignore those orphans at the read boundary rather than deleting
	// them, because:
	//   - non-destructive: once the upstream survey source is deleted, the vlab
	//     copy is the only surviving record of those responses;
	//   - reversible: re-adding the source to the conf lights its history back up;
	//   - it matches the event-sourced design of study_run_events (never mutate
	//     facts; derive the current view).
	// It also stops orphaned sources from tripping an "unmapped source" warning on
	// every run — that warning was event-anchored (see the skip branch in
	// inference-data Reduce); the authority is the config, not the event tags.
	// See planning/swoosh-config-reconciliation.md.
	events, err := GetEvents(pool, study, mapping.Sources())
	if err != nil {
		err = fmt.Errorf("study %s: reading events: %w", study, err)
		recordRunOutcome(pool, study, runID, eventRunError, severityError, err.Error(), "read")
		return err
	}
	log.Printf("Swoosh read %d events.\n", len(events))

	id, extractionErrors, err := Reduce(events, mapping)
	if err != nil {
		err = fmt.Errorf("study %s: reduce: %w", study, err)
		recordRunOutcome(pool, study, runID, eventRunError, severityError, err.Error(), "reduce")
		return err
	}

	log.Printf("Swoosh had %d extractionErrors\n", len(extractionErrors))
	for _, e := range extractionErrors {
		log.Println(e.Error())
		recordExtractionError(pool, study, runID, e)
	}

	log.Printf("Swoosh storing InferenceData from %d users\n", len(id))
	if err := WriteInferenceData(pool, study, id); err != nil {
		err = fmt.Errorf("study %s: writing inference data: %w", study, err)
		recordRunOutcome(pool, study, runID, eventRunError, severityError, err.Error(), "write")
		return err
	}

	recordRunOutcome(pool, study, runID, eventRunOK, "", "", "")
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
