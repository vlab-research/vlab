package main

import (
	"context"
	"encoding/json"

	"github.com/jackc/pgx/v4"
	"github.com/jackc/pgx/v4/pgxpool"
)

func InsertInferenceData(tx pgx.Tx, study, user, variable string, data []byte) error {
	query := `
            INSERT INTO inference_data (study, user_id, variable, data) VALUES ($1, $2, $3, $4)
            ON CONFLICT (study, user_id, variable) DO UPDATE SET data = $4
        `

	_, err := tx.Exec(context.Background(), query, study, user, variable, data)

	return err
}

func WriteInferenceData(pool *pgxpool.Pool, study string, id InferenceData) error {
	tx, err := pool.Begin(context.Background())
	if err != nil {
		return err
	}

	// TODO: this is very expensive and silly, should be optimized
	_, err = tx.Exec(context.Background(), "DELETE FROM inference_data WHERE study = $1", study)

	if err != nil {
		return err
	}

	for user, row := range id {
		for variable, row := range row.Data {
			d, err := json.Marshal(row)

			if err != nil {
				return err
			}

			err = InsertInferenceData(tx, study, user, variable, d)
			if err != nil {
				return err
			}
		}

	}

	tx.Commit(context.Background())

	return nil
}
