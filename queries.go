package main

import (
	"context"
	"log"

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
              AND updated > (NOW() - ($1)::INTERVAL)
              AND (NOW() - updated) > interval '1 hour'`

	return get(conn, getRedo, query, cfg.RespondingInterval)
}

func blocked(cfg *Config, conn *pgxpool.Pool) chan *ExternalEvent {

	query := `SELECT userid, pageid
              FROM states
              WHERE current_state = 'BLOCKED'
              AND fb_error_code = ANY($1)
              AND updated > (NOW() - ($2)::INTERVAL)`

	return get(conn, getRedo, query, redoCodes(cfg), cfg.BlockedInterval)
}

func timeouts(cfg *Config, conn *pgxpool.Pool) chan *ExternalEvent {

	query := `SELECT timeout_date, userid, pageid 
              FROM states 
              WHERE current_state = 'WAIT_EXTERNAL_EVENT' 
              AND timeout_date < NOW()`

	return get(conn, getTimeout, query)
}
