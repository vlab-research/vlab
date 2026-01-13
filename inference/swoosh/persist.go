package main

import (
	"context"
	"fmt"

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

// batchInsertInferenceData performs batch INSERTs for improved performance
// Uses a conservative batch size of 500 rows to balance memory usage and performance
func batchInsertInferenceData(tx pgx.Tx, study string, id InferenceData) error {
	const batchSize = 500

	// Pre-allocate slices to reduce GC pressure
	type rowData struct {
		user      string
		variable  string
		valueType string
		value     []byte
		timestamp time.Time
	}
	rows := make([]rowData, 0, batchSize)

	// Helper function to flush current batch
	flushBatch := func() error {
		if len(rows) == 0 {
			return nil
		}

		// Build parameterized query dynamically based on batch size
		// Each row has 6 parameters: study_id, user_id, variable, value_type, value, timestamp
		query := "INSERT INTO inference_data (study_id, user_id, variable, value_type, value, timestamp) VALUES "
		args := make([]interface{}, 0, len(rows)*6)

		for i, row := range rows {
			if i > 0 {
				query += ", "
			}
			// Calculate parameter indices for this row
			base := i * 6
			query += fmt.Sprintf("($%d, $%d, $%d, $%d, $%d, $%d)", base+1, base+2, base+3, base+4, base+5, base+6)
			args = append(args, study, row.user, row.variable, row.valueType, row.value, row.timestamp)
		}

		query += " ON CONFLICT (study_id, user_id, variable) DO UPDATE SET value = EXCLUDED.value, timestamp = EXCLUDED.timestamp"

		_, err := tx.Exec(context.Background(), query, args...)
		if err != nil {
			return err
		}

		// Clear batch
		rows = rows[:0]
		return nil
	}

	// Iterate through all data and batch inserts
	for user, row := range id {
		for variable, dataValue := range row.Data {
			rows = append(rows, rowData{
				user:      user,
				variable:  variable,
				valueType: dataValue.ValueType,
				value:     dataValue.Value,
				timestamp: dataValue.Timestamp,
			})

			// Flush when batch is full
			if len(rows) >= batchSize {
				if err := flushBatch(); err != nil {
					return err
				}
			}
		}
	}

	// Flush remaining rows
	return flushBatch()
}

func WriteInferenceData(pool *pgxpool.Pool, study string, id InferenceData) error {
	tx, err := pool.Begin(context.Background())
	if err != nil {
		return err
	}

	// Ensure rollback on error
	defer func() {
		if err != nil {
			tx.Rollback(context.Background())
		}
	}()

	// TODO: this is very expensive and silly, should be optimized
	_, err = tx.Exec(context.Background(), "DELETE FROM inference_data WHERE study_id = $1", study)
	if err != nil {
		return err
	}

	// Use batch insert for improved performance
	err = batchInsertInferenceData(tx, study, id)
	if err != nil {
		return err
	}

	return tx.Commit(context.Background())
}
