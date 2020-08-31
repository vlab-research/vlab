package main

import (
	"time"
	"context"

	"github.com/jackc/pgx/v4"
	"github.com/jackc/pgx/v4/pgxpool"
)


type Event struct {
	Type string `json:"type"`
	Value string `json:"value,omitempty"` // rawmesssage??
}

type ExternalEvent struct {
	User string `json:"user"`
	Page string `json:"page"`
	Event *Event `json:"event"`
}

type EventMaker func (pgx.Rows) *ExternalEvent

func get(conn *pgxpool.Pool, fn EventMaker, query string, args ...interface{}) chan *ExternalEvent {
	ch := make(chan *ExternalEvent)

    rows, err := conn.Query(context.Background(), query, args...)
	handle(err)

	go func () {
		defer rows.Close()
		defer close(ch)

		for rows.Next() {
			ch <- fn(rows)
		}
	}()

	return ch
}

func getRedo(rows pgx.Rows) *ExternalEvent {
	var userid, pageid string
	err := rows.Scan(&userid, &pageid)
	handle(err)
	return &ExternalEvent{userid, pageid, &Event{"redo", ""}}
}

func getTimeout(rows pgx.Rows) *ExternalEvent {
	var timeoutDate, userid, pageid string
	err := rows.Scan(&timeoutDate, &userid, &pageid)
	handle(err)
	return &ExternalEvent{userid, pageid, &Event{"redo", timeoutDate}}
}

func respondings(cfg *Config, conn *pgxpool.Pool) chan *ExternalEvent {
	query := `SELECT userid, pageid
              FROM states
              WHERE current_state = 'RESPONDING'
              AND updated > $2 - ($1)::INTERVAL
              AND now() - updated > interval '1 hour'`

	return get(conn, getRedo, query, cfg.RespondingInterval, time.Now())
}

func blocked(cfg *Config, conn *pgxpool.Pool) chan *ExternalEvent {
	query := `SELECT userid, pageid
              FROM states
              WHERE state_json->'error'->>'code' = ANY($1)
              AND updated > $3 - ($2)::INTERVAL`

	return get(conn, getRedo, query, redoCodes(cfg), cfg.BlockedInterval, time.Now())
}

func timeouts(cfg *Config, conn *pgxpool.Pool) chan *ExternalEvent {
	query := `WITH s AS
                (WITH t AS
                  (SELECT
                     CEILING((state_json->>'waitStart')::INT/1000)::INT::TIMESTAMPTZ as wait_start,
                     (state_json->'wait'->>'value')::INTERVAL AS wait_time,
                     userid,
                     pageid
                   FROM states
                   WHERE current_state = 'WAIT_EXTERNAL_EVENT')
                 SELECT
                   wait_start + wait_time as timeout_date,
                   *
                 FROM t)
              SELECT timeout_date, userid, pageid
              FROM s
              WHERE timeout_date < $1`

	return get(conn, getTimeout, query, time.Now())
}
