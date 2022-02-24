package connector

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"time"

	"github.com/caarlos0/env/v6"
	"github.com/jackc/pgx/v4"
	"github.com/jackc/pgx/v4/pgxpool"
)

func handle(err error) {
	if err != nil {
		log.Fatal(err)
	}
}

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

type Connector interface {
	Handler(source *Source, lastEvent *InferenceDataEvent) <-chan *InferenceDataEvent
}

func GetStudyConfs(pool *pgxpool.Pool, dataSource string) ([]*Source, error) {
	query := `
        WITH tt AS (
	  WITH t AS (
	    SELECT conf,
		   study_id,
		   ROW_NUMBER() OVER (PARTITION BY study_id ORDER BY study_confs.created DESC) AS n
	    FROM study_confs
	    INNER JOIN study_state on study_confs.study_id = study_state.id
	    WHERE conf_type = 'data_source'
            AND study_state.active = true
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

func LastEvent(pool *pgxpool.Pool, source *Source, orderBy string) (*InferenceDataEvent, bool, error) {
	match := false
	for _, opt := range []string{"timestamp", "idx", "pagination"} {
		if orderBy == opt {
			match = true
			break
		}
	}

	if match == false {
		return nil, false, fmt.Errorf("Column %s is not a valid order by column", orderBy)
	}

	query := `
	SELECT data
        FROM inference_data_events
        WHERE study_id = $1 AND source_name = $2
        ORDER BY %s DESC
        LIMIT 1
	`
	query = fmt.Sprintf(query, orderBy)

	e := new(InferenceDataEvent)
	err := pool.QueryRow(context.Background(), query, source.StudyID, source.Conf.Name).Scan(e)

	if err == pgx.ErrNoRows {
		return nil, false, nil
	}

	if err != nil {
		return nil, false, err
	}

	return e, true, nil
}

type Config struct {
	DB string `env:"PG_URL,required"` // postgres://user:password@host:port/db
	// KafkaBrokers     string        `env:"KAFKA_BROKERS,required"`
	// KafkaPollTimeout time.Duration `env:"KAFKA_POLL_TIMEOUT,required"`
	// Topic            string        `env:"KAFKA_TOPIC,required"`
	// Group            string        `env:"KAFKA_GROUP,required"`
}

func (cfg *Config) load() *Config {
	err := env.Parse(cfg)
	handle(err)
	return cfg
}

func LoadEvents(connector Connector, dataSource string, orderColumn string) {
	cnf := &Config{}
	cnf = cnf.load()

	pool, err := pgxpool.Connect(context.Background(), cnf.DB)
	handle(err)

	sources, err := GetStudyConfs(pool, dataSource)
	handle(err)

	fmt.Println(sources)

	// this doesn't need to be done sequentially,
	// make a go loop?
	for _, source := range sources {

		e, _, err := LastEvent(pool, source, orderColumn)
		handle(err)

		events := connector.Handler(source, e)

		written, err := WriteEvents(pool, source.StudyID, events)
		log.Println(fmt.Sprintf("Wrote %d results to the event store", written))
		handle(err)
	}

}
