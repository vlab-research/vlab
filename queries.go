
package main

import (
	"context"
	"encoding/json"

	"github.com/jackc/pgx/v4"
	"github.com/jackc/pgx/v4/pgxpool"
)


type Event struct {
	Type string `json:"type"`
	Value *json.RawMessage `json:"value,omitempty"`
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

	return &ExternalEvent{userid, pageid, &Event{"redo", nil}}
}

func getTimeout(rows pgx.Rows) *ExternalEvent {
	var waitStart int64
	var userid, pageid string
	err := rows.Scan(&waitStart, &userid, &pageid)
	handle(err)

	b, _ := json.Marshal(waitStart)
	value := json.RawMessage(b)

	return &ExternalEvent{userid, pageid, &Event{"timeout", &value}}
}


func getFollowUp(rows pgx.Rows) *ExternalEvent {
	var question string
	var userid, pageid string
	err := rows.Scan(&question, &userid, &pageid)
	handle(err)

	b, _ := json.Marshal(question)
	value := json.RawMessage(b)

	return &ExternalEvent{userid, pageid, &Event{"follow_up", &value}}
}

func Respondings(cfg *Config, conn *pgxpool.Pool) <-chan *ExternalEvent {
	query := `SELECT userid, pageid
              FROM states
              WHERE
                current_state = 'RESPONDING' AND
                updated > (NOW() - ($1)::INTERVAL) AND
                (NOW() - updated) > ($2)::INTERVAL`

	return get(conn, getRedo, query, cfg.RespondingInterval, cfg.RespondingGrace)
}

func Blocked(cfg *Config, conn *pgxpool.Pool) <-chan *ExternalEvent {

	query := `SELECT userid, pageid
              FROM states
              WHERE
                current_state = 'BLOCKED' AND
                fb_error_code = ANY($1) AND
                updated > (NOW() - ($2)::INTERVAL)`

	return get(conn, getRedo, query, redoCodes(cfg), cfg.BlockedInterval)
}

func Timeouts(cfg *Config, conn *pgxpool.Pool) <-chan *ExternalEvent {
	query := `SELECT (state_json->>'waitStart')::int, userid, pageid
              FROM states
              WHERE current_state = 'WAIT_EXTERNAL_EVENT' AND
                timeout_date < NOW()`

	return get(conn, getTimeout, query)
}

// TODO: test cockroach perf and index
func FollowUps(cfg *Config, conn *pgxpool.Pool) <-chan *ExternalEvent {
	query := `SELECT state_json->>'question', userid, pageid
              FROM states
              WHERE
                current_state = 'QOUT'  AND
                (state_json->'previousOutput'->>'followUp') IS NULL AND
                (state_json->'previousOutput'->>'token') IS NULL AND
                (NOW() - updated) > ($1)::INTERVAL AND
                (NOW() - updated) < ($2)::INTERVAL`

	return get(conn, getFollowUp, query, cfg.FollowUpMin, cfg.FollowUpMax)
}
