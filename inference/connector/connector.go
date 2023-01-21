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
	. "github.com/vlab-research/vlab/inference/inference-data"
)

func handle(err error) {
	if err != nil {
		log.Fatal(err)
	}
}

// -------------------------------
// TODO: move to shared library, currently copy-pasted here
// temporarily

type Connector interface {
	Handler(source *Source, lastEvent *InferenceDataEvent) <-chan *InferenceDataEvent
}

func GetStudyConfs(pool *pgxpool.Pool, dataSource string) ([]*Source, error) {
	query := `
        WITH tt AS (
	  WITH t AS (
	    SELECT conf,
                   user_id,
		   study_id,
		   ROW_NUMBER() OVER (PARTITION BY study_id ORDER BY study_confs.created DESC) AS n
	    FROM study_confs
	    INNER JOIN study_state on study_confs.study_id = study_state.id
	    WHERE conf_type = 'data_sources'
            AND study_state.start_date < $1
            AND study_state.end_date > $1

	  )
	  SELECT json_array_elements(conf) as conf,
		 study_id,
                 user_id
	  FROM t
	  WHERE n = 1
	)
        SELECT conf,
               study_id,
               credentials.entity,
               credentials.key,
               credentials.details,
               credentials.created
        FROM tt
        INNER JOIN credentials
           ON credentials.user_id = tt.user_id
           AND credentials.entity =  $2
           AND credentials.key = tt.conf->>'credentials_key'
        WHERE conf->>'source' = $2
        `

	res := []*Source{}
	now := time.Now().UTC() // extract?
	rows, err := pool.Query(context.Background(), query, now, dataSource)
	if err != nil {
		return nil, err
	}

	for rows.Next() {
		cnf := new(SourceConf)
		var study string
		var entity string
		var key string
		details := new(json.RawMessage)
		created := new(time.Time)

		err := rows.Scan(cnf, &study, &entity, &key, details, created)

		// TODO: make better error handling.
		// one problem with putting the credentials in the query itself is that you will just
		// get no results if credentials don't exist, which is a form of silent failure
		// So while it seemed slick, maybe it's not as good as having a separate GetCredentials..
		// with cnf.CredentialsKey, and dataSource, and study...

		if err != nil {
			return nil, err
		}

		res = append(res, &Source{
			StudyID: study,
			Conf:    cnf,
			Credentials: &Credentials{
				Entity:  entity,
				Key:     key,
				Details: *details,
				Created: *created,
			},
		})
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
