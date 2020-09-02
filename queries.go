
package main

import (
	"context"
	"time"

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
type Query func (*Config, *pgxpool.Pool) <-chan *ExternalEvent

func get(conn *pgxpool.Pool, fn EventMaker, query string, args ...interface{}) <-chan *ExternalEvent {
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
	var timeoutDate time.Time
	var userid, pageid string
	err := rows.Scan(&timeoutDate, &userid, &pageid)
	handle(err)

	ts := timeoutDate.UTC().Format(time.RFC3339)
	return &ExternalEvent{userid, pageid, &Event{"timeout", ts}}
}

func Respondings(cfg *Config, conn *pgxpool.Pool) <-chan *ExternalEvent {
	query := `SELECT userid, pageid
              FROM states
              WHERE current_state = 'RESPONDING'
              AND updated > (NOW() - ($1)::INTERVAL)
              AND (NOW() - updated) > ($2)::INTERVAL`

	return get(conn, getRedo, query, cfg.RespondingInterval, cfg.RespondingGrace)
}

func Blocked(cfg *Config, conn *pgxpool.Pool) <-chan *ExternalEvent {

	query := `SELECT userid, pageid
              FROM states
              WHERE current_state = 'BLOCKED'
              AND fb_error_code = ANY($1)
              AND updated > (NOW() - ($2)::INTERVAL)`

	return get(conn, getRedo, query, redoCodes(cfg), cfg.BlockedInterval)
}

func Timeouts(cfg *Config, conn *pgxpool.Pool) <-chan *ExternalEvent {
	query := `SELECT timeout_date, userid, pageid 
              FROM states 
              WHERE current_state = 'WAIT_EXTERNAL_EVENT' 
              AND timeout_date < NOW()`

	return get(conn, getTimeout, query)
}
