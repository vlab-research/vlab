package main

import (
	"encoding/json"
	"fmt"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
)


const (
	stateSql = `drop table if exists states;
                create table if not exists states(
     			  userid VARCHAR NOT NULL,
				  pageid VARCHAR NOT NULL NOT NULL,
				  updated TIMESTAMPTZ NOT NULL,
				  current_state VARCHAR NOT NULL,
				  state_json JSON NOT NULL,
                  timeout_date TIMESTAMPTZ AS (CEILING((state_json->>'waitStart')::INT/1000)::INT::TIMESTAMPTZ + (state_json->'wait'->>'value')::INTERVAL) STORED,
                  fb_error_code varchar AS (state_json->'error'->>'code') STORED,
                  CONSTRAINT "valid_state_json" CHECK (state_json ? 'state'),
				  PRIMARY KEY (userid, pageid)
           );`

	insertQuery = `INSERT INTO 
                   states(userid, pageid, updated, current_state, state_json) 
                   VALUES ($1, $2, $3, $4, $5)`	
)

func getEvents(ch <-chan *ExternalEvent) []*ExternalEvent {
	events := []*ExternalEvent{}
	for e := range ch {
		events = append(events, e)
	}
	return events
}

func TestGetRespondingsGetsOnlyThoseInGivenInterval(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, stateSql)
	mustExec(t, pool, insertQuery, 
		"foo", 
		"bar", 
		time.Now().Add(-2*time.Hour), 
		"RESPONDING", 
		`{"state": "RESPONDING"}`)

	mustExec(t, pool, insertQuery, 
		"baz", 
		"bar", 
		time.Now().Add(-6*time.Hour), 
		"RESPONDING",
		`{"state": "RESPONDING"}`)

	cfg := &Config{RespondingInterval: "4 hours", RespondingGrace: "1 hour"}
	ch := Respondings(cfg, pool)
	events := getEvents(ch)


	assert.Equal(t, 1, len(events))
	assert.Equal(t, "foo", events[0].User)

	mustExec(t, pool, "drop table states")
}

func TestGetRespondingsOnlyGetsThoseOutsideOfGracePeriod(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, stateSql)
	mustExec(t, pool, insertQuery, 
		"foo", 
		"bar", 
		time.Now().Add(-30*time.Minute), 
		"RESPONDING", 
		`{"state": "RESPONDING"}`)

	mustExec(t, pool, insertQuery, 
		"baz", 
		"bar", 
		time.Now().Add(-90*time.Minute), 
		"RESPONDING", 
		`{"state": "RESPONDING"}`)

	cfg := &Config{RespondingInterval: "4 hours", RespondingGrace: "1 hour"}
	ch := Respondings(cfg, pool)
	events := getEvents(ch)

	assert.Equal(t, 1, len(events))
	assert.Equal(t, "baz", events[0].User)

	mustExec(t, pool, "drop table states")
}

func TestGetBlockedOnlyGetsThoseWithCodesInsideWindow(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, stateSql)
	mustExec(t, pool, insertQuery, 
		"foo", 
		"bar", 
		time.Now().Add(-30*time.Minute), 
		"BLOCKED", 
		`{"state": "BLOCKED", "error": {"code": 2020}}`)
	mustExec(t, pool, insertQuery, 
		"baz", 
		"bar", 
		time.Now().Add(-30*time.Minute), 
		"BLOCKED", 
		`{"state": "BLOCKED", "error": {"code": 9999}}`)
	mustExec(t, pool, insertQuery, 
		"qux", 
		"bar", 
		time.Now().Add(-90*time.Minute), 
		"BLOCKED", 
		`{"state": "BLOCKED", "error": {"code": 2020}}`)

	cfg := &Config{BlockedInterval: "1 hour", Codes: "2020,-1"}
	ch := Blocked(cfg, pool)
	events := getEvents(ch)

	assert.Equal(t, 1, len(events))
	assert.Equal(t, "foo", events[0].User)

	mustExec(t, pool, "drop table states")
}

func TestGetTimeoutsGetsOnlyExpiredTimeouts(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	ts := time.Now().UTC().Add(-30*time.Minute)
	ms := ts.Unix()*1000

	mustExec(t, pool, stateSql)
	mustExec(t, pool, insertQuery, 
		"foo", 
		"bar", 
		ts, 
		"WAIT_EXTERNAL_EVENT", 
		fmt.Sprintf(`{"state": "WAIT_EXTERNAL_EVENT", 
                      "waitStart": %v, 
                      "wait": { "value": "20 minutes"}}`, ms))

	mustExec(t, pool, insertQuery, 
		"baz", 
		"bar", 
		ts, 
		"WAIT_EXTERNAL_EVENT", 
		fmt.Sprintf(`{"state": "WAIT_EXTERNAL_EVENT", 
                      "waitStart": %v, 
                      "wait": { "value": "40 minutes"}}`, ms))

	cfg := &Config{}
	ch := Timeouts(cfg, pool)
	events := getEvents(ch)

	assert.Equal(t, 1, len(events))
	assert.Equal(t, "foo", events[0].User)

	assert.Equal(t, "timeout", events[0].Event.Type)

	
	ev, _ := json.Marshal(events[0].Event)
	assert.Equal(t, string(ev), fmt.Sprintf(`{"type":"timeout","value":%v}`, ms))

	mustExec(t, pool, "drop table states")
}


func TestFollowUpsGetsOnlyThoseBetweenMinAndMaxAndNotFollowedUp(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, stateSql)
	mustExec(t, pool, insertQuery, 
		"foo", 
		"bar", 
		time.Now().UTC().Add(-30*time.Minute),
		"QOUT", 
		`{"state": "QOUT", "question": "foo", "previousOutput": {"followUp": null}}`)

	mustExec(t, pool, insertQuery, 
		"bar", 
		"qux", 
		time.Now().UTC().Add(-30*time.Minute),
		"QOUT", 
		`{"state": "QOUT", "question": "foo", "previousOutput": {"followUp": true}}`)

	mustExec(t, pool, insertQuery, 
		"baz", 
		"bar", 
		time.Now().UTC().Add(-90*time.Minute),
		"QOUT", 
		`{"state": "QOUT", "question": "foo"}`)

	cfg := &Config{FollowUpMin: "20 minutes", FollowUpMax: "60 minutes"}
	ch := FollowUps(cfg, pool)
	events := getEvents(ch)

	assert.Equal(t, 1, len(events))
	assert.Equal(t, "foo", events[0].User)
	assert.Equal(t, "follow_up", events[0].Event.Type)

	ev, _ := json.Marshal(events[0].Event)
	assert.Equal(t, string(ev), `{"type":"follow_up","value":"foo"}`)

	mustExec(t, pool, "drop table states")
}
