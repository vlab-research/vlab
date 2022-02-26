package main

import (
	"context"

	"github.com/jackc/pgx/v4"
	"github.com/jackc/pgx/v4/pgxpool"
	. "github.com/vlab-research/vlab/inference/inference-data"
	"time"
)

func InsertInferenceData(tx pgx.Tx, study, user, variable, valueType string, value []byte, timestamp time.Time) error {
	query := `
            INSERT INTO inference_data (study_id, user_id, variable, value_type, value, timestamp) VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (study_id, user_id, variable) DO UPDATE SET value = $5, timestamp = $6
        `

	_, err := tx.Exec(context.Background(), query, study, user, variable, valueType, value, timestamp)

	return err
}

func WriteInferenceData(pool *pgxpool.Pool, study string, id InferenceData) error {
	tx, err := pool.Begin(context.Background())
	if err != nil {
		return err
	}

	// TODO: this is very expensive and silly, should be optimized
	_, err = tx.Exec(context.Background(), "DELETE FROM inference_data WHERE study_id = $1", study)

	if err != nil {
		return err
	}

	for user, row := range id {
		for variable, row := range row.Data {

			err = InsertInferenceData(tx, study, user, variable, row.ValueType, row.Value, row.Timestamp)
			if err != nil {
				return err
			}
		}

	}

	tx.Commit(context.Background())

	return nil
}
