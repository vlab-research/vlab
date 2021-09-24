package main

import (
	"context"
	"encoding/json"
	"github.com/jackc/pgx/v4/pgxpool"
	"time"
)

// -------------------------------
// TODO: move to shared library, currently copy-pasted here
// temporarily
type User struct {
	ID       string                     `json:"id"`
	Metadata map[string]json.RawMessage `json:"metadata"`
}
type InferenceDataEvent struct {
	User       User            `json:"user"`
	Study      string          `json:"study"`
	DataSource string          `json:"data_source"`
	Timestamp  time.Time       `json:"timestamp"`
	Variable   string          `json:"variable"`
	Value      json.RawMessage `json:"value"`
}

// -------------------------------

type SourceConf struct {
	Source string          `json:"source"`
	Config json.RawMessage `json:"config"`
}

type Source struct {
	StudyID string
	Conf    *SourceConf
}

// DB reprsentation of configuration of data sources for a study
type DataSourceConf []*SourceConf

func GetStudyConfs(pool *pgxpool.Pool, dataSource string) ([]*Source, error) {
	query := `
        WITH t AS (
	  SELECT json_array_elements(conf) as conf,
                 study_id,
                 ROW_NUMBER() OVER (PARTITION BY study_id ORDER BY created DESC) AS n
	  FROM study_confs
	  INNER JOIN studies on study_confs.study_id = studies.id
	  WHERE conf_type = 'data_source'
	  AND active = true
        )
        SELECT conf, study_id FROM t WHERE n = 1 AND conf->>'source' = $1;
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
