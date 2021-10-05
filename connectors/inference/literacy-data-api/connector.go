package main

import (
	"context"
	"encoding/json"
	"time"

	"github.com/jackc/pgx/v4"
	"github.com/jackc/pgx/v4/pgxpool"
)

// -------------------------------
// TODO: move to shared library, currently copy-pasted here
// temporarily
type User struct {
	ID       string                     `json:"id"`
	Metadata map[string]json.RawMessage `json:"metadata"`
}

type SourceConf struct {
	Name   string          `json:"name"`
	Source string          `json:"source"`
	Config json.RawMessage `json:"config"`
}

type InferenceDataEvent struct {
	User       User            `json:"user"`
	Study      string          `json:"study"`
	SourceConf *SourceConf     `json:"source_conf"`
	Timestamp  time.Time       `json:"timestamp"`
	Variable   string          `json:"variable"`
	Value      json.RawMessage `json:"value"`
	Idx        int             `json:"idx"`
	Pagination string          `json:"pagination"`
}

// -------------------------------

type Source struct {
	StudyID string
	Conf    *SourceConf
}

// DB reprsentation of configuration of data sources for a study
type DataSourceConf []*SourceConf

func GetStudyConfs(pool *pgxpool.Pool, dataSource string) ([]*Source, error) {
	query := `
        WITH tt AS (
	  WITH t AS (
	    SELECT conf,
		   study_id,
		   ROW_NUMBER() OVER (PARTITION BY study_id ORDER BY created DESC) AS n
	    FROM study_confs
	    INNER JOIN studies on study_confs.study_id = studies.id
	    WHERE conf_type = 'data_source'
	    AND active = true
	  )
	  SELECT json_array_elements(conf) as conf,
		 study_id
	  FROM t
	  WHERE n = 1
	)
        SELECT * from tt WHERE conf->>'source' = $1
        `

	res := []*Source{}
	rows, err := pool.Query(context.Background(), query, dataSource)
	if err != nil {
		return nil, err
	}

	for rows.Next() {
		cnf := new(SourceConf)
		var study string
		err := rows.Scan(cnf, &study)
		if err != nil {
			return nil, err
		}

		// where do I put study??????
		res = append(res, &Source{study, cnf})
	}

	return res, nil
}

func WriteEvents(pool *pgxpool.Pool, study string, events <-chan *InferenceDataEvent) (int, error) {
	query := `
        INSERT INTO inference_data_events(study_id, source_name, timestamp, data, idx, pagination) values($1, $2, $3, $4, $5, $6)
        `
	i := 0
	for e := range events {
		i++
		b, err := json.Marshal(e)
		if err != nil {
			return i, err
		}
		_, err = pool.Exec(
			context.Background(),
			query,
			study,
			e.SourceConf.Name,
			e.Timestamp,
			b,
			e.Idx,
			e.Pagination,
		)
		if err != nil {
			return i, err
		}
	}

	return i, nil
}

func LastEvent(pool *pgxpool.Pool, source *Source) (int, string, bool, error) {
	query := `
	SELECT idx, pagination
        FROM inference_data_events
        WHERE study_id = $1 AND source_name = $2
        ORDER BY TIMESTAMP DESC
        LIMIT 1
	`
	var idx int
	var pagination string
	err := pool.QueryRow(context.Background(), query, source.StudyID, source.Conf.Name).Scan(&idx, &pagination)

	if err == pgx.ErrNoRows {
		return 0, "", false, nil
	}

	if err != nil {
		return 0, "", false, err
	}

	return idx, pagination, true, nil
}
