package main

import "github.com/jackc/pgx/v4/pgxpool"

func GetUsersMissingAssignments(pool *pgxpool.Pool, conf *TarotConfig) TreatmentAssignmentParams {

	// json_object_agg()

	// q := `
	//     SELECT user_id
	//     FROM inference_data
	//     WHERE study_id = $1

	//     -- opposite of union

	//     SELECT

	// `

	params := TreatmentAssignmentParams{
		// requests
	}

	return params
}
