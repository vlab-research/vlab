package main

import (
	"encoding/json"
	"fmt"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
)

const (
	surveySql = `drop table if exists surveys;
                 create table if not exists surveys(
                   userid VARCHAR NOT NULL,
                   shortcode VARCHAR NOT NULL,
                   messages_json JSON,
                   created TIMESTAMPTZ NOT NULL,
                   has_followup BOOL AS (messages_json->>'label.buttonHint.default' IS NOT NULL) STORED
                 );

                drop table if exists credentials;
                create table if not exists credentials(
                    userid VARCHAR NOT NULL,
		    entity VARCHAR NOT NULL,
		    key VARCHAR NOT NULL UNIQUE,
		    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
		    details JSONB NOT NULL,
		    facebook_page_id VARCHAR AS (CASE WHEN entity = 'facebook_page' THEN details->>'id' ELSE NULL END) STORED,
		    UNIQUE(entity, key),
                    UNIQUE(facebook_page_id)
                );
        `

	pageInsertSql   = `INSERT INTO credentials(entity, key, userid, details) VALUES ('facebook_page', ($1)->>'id', 'owner', $1)`
	surveyInsertSql = `INSERT INTO surveys(userid, shortcode, created, messages_json) VALUES ('owner', $1, $2, $3);`

	stateSql = `drop table if exists states;
                create table if not exists states(
   	          userid VARCHAR NOT NULL,
		  pageid VARCHAR NOT NULL NOT NULL,
		  updated TIMESTAMPTZ NOT NULL,
		  current_state VARCHAR NOT NULL,
		  state_json JSON NOT NULL,
                  current_form VARCHAR AS (state_json->'forms'->>-1) STORED,
                  form_start_time TIMESTAMPTZ AS (CEILING((state_json->'md'->>'startTime')::INT/1000)::INT::TIMESTAMPTZ) STORED,
                  previous_with_token BOOL AS (state_json->'previousOutput'->>'token' IS NOT NULL) STORED,
                  previous_is_followup BOOL AS (state_json->'previousOutput'->>'followUp' IS NOT NULL) STORED,
		  timeout_date TIMESTAMPTZ AS (CASE
			WHEN state_json->'wait'->>'type' = 'timeout' THEN (CEILING((state_json->>'waitStart')::INT/1000)::INT::TIMESTAMPTZ + (state_json->'wait'->>'value')::INTERVAL)
			ELSE NULL
		  END) STORED,
                  fb_error_code varchar AS (state_json->'error'->>'code') STORED,
                  error_tag VARCHAR AS (state_json->'error'->>'tag') STORED,
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

	cfg := &Config{BlockedInterval: "1 hour", Codes: []string{"2020", "-1"}}
	ch := Blocked(cfg, pool)
	events := getEvents(ch)

	assert.Equal(t, 1, len(events))
	assert.Equal(t, "foo", events[0].User)

	mustExec(t, pool, "drop table states")
}

func TestGetErroredGetsByTag(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, stateSql)
	mustExec(t, pool, insertQuery,
		"foo",
		"bar",
		time.Now().Add(-30*time.Minute),
		"ERROR",
		`{"state": "ERROR", "error": {"tag": "NETWORK"}}`)
	mustExec(t, pool, insertQuery,
		"baz",
		"bar",
		time.Now().Add(-30*time.Minute),
		"ERROR",
		`{"state": "ERROR", "error": {"tag": "NOTNET"}}`)

	cfg := &Config{ErrorInterval: "1 hour", ErrorTags: []string{"NETWORK"}}
	ch := Errored(cfg, pool)
	events := getEvents(ch)

	assert.Equal(t, 1, len(events))
	assert.Equal(t, "foo", events[0].User)

	mustExec(t, pool, "drop table states")
}

func TestGetTimeoutsGetsOnlyExpiredTimeouts(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	ts := time.Now().UTC().Add(-30 * time.Minute)
	ms := ts.Unix() * 1000

	mustExec(t, pool, stateSql)
	mustExec(t, pool, insertQuery,
		"foo",
		"bar",
		ts,
		"WAIT_EXTERNAL_EVENT",
		fmt.Sprintf(`{"state": "WAIT_EXTERNAL_EVENT",
                      "waitStart": %v,
                      "wait": { "type": "timeout", "value": "20 minutes"}}`, ms))

	mustExec(t, pool, insertQuery,
		"baz",
		"bar",
		ts,
		"WAIT_EXTERNAL_EVENT",
		fmt.Sprintf(`{"state": "WAIT_EXTERNAL_EVENT",
                      "waitStart": %v,
                      "wait": { "type": "timeout", "value": "40 minutes"}}`, ms))

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

func makeStateJson(startTime time.Time, form, previousOutput string) string {
	base := `{"state": "QOUT", "md": { "startTime": %v }, "forms": ["%v"], "question": "foo", "previousOutput": %v }`

	return fmt.Sprintf(base, startTime.Unix()*1000, form, previousOutput)
}

func TestFollowUpsGetsOnlyThoseBetweenMinAndMaxAndIgnoresAllSortsOfThings(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, stateSql)
	mustExec(t, pool, surveySql)

	mustExec(t, pool, pageInsertSql, `{"id": "bar"}`)
	mustExec(t, pool, pageInsertSql, `{"id": "qux"}`)
	mustExec(t, pool, pageInsertSql, `{"id": "quux"}`)
	mustExec(t, pool, surveyInsertSql, "with_followup", time.Now().UTC().Add(-50*time.Hour), `{"label.buttonHint.default": "this is follow up"}`)
	mustExec(t, pool, surveyInsertSql, "with_followup", time.Now().UTC().Add(-40*time.Hour), `{"label.buttonHint.default": "this is follow up"}`)
	mustExec(t, pool, surveyInsertSql, "with_followup", time.Now().UTC().Add(-20*time.Hour), `{"label.other": "not a follow up"}`)
	mustExec(t, pool, surveyInsertSql, "without_followup", time.Now().UTC().Add(-20*time.Hour), `{"label.other": "not a follow up"}`)

	mustExec(t, pool, insertQuery,
		"foo",
		"bar",
		time.Now().UTC().Add(-30*time.Minute),
		"QOUT",
		makeStateJson(time.Now().UTC().Add(-30*time.Hour), "with_followup", `{"followUp": null}`))

	mustExec(t, pool, insertQuery,
		"quux",
		"bar",
		time.Now().UTC().Add(-30*time.Minute),
		"QOUT",
		makeStateJson(time.Now().UTC().Add(-10*time.Hour), "with_followup", `{"followUp": null}`))

	mustExec(t, pool, insertQuery,
		"baz",
		"bar",
		time.Now().UTC().Add(-30*time.Minute),
		"QOUT",
		makeStateJson(time.Now().UTC().Add(-60*time.Hour), "without_followup", `{"followUp": null}`))

	mustExec(t, pool, insertQuery,
		"bar",
		"qux",
		time.Now().UTC().Add(-30*time.Minute),
		"QOUT",
		makeStateJson(time.Now().UTC().Add(-60*time.Hour), "with_followup", `{"followUp": true}`))

	mustExec(t, pool, insertQuery,
		"bar",
		"quux",
		time.Now().UTC().Add(-30*time.Minute),
		"QOUT",
		makeStateJson(time.Now().UTC().Add(-60*time.Hour), "with_followup", `{"token": "token"}`))

	mustExec(t, pool, insertQuery,
		"qux",
		"bar",
		time.Now().UTC().Add(-90*time.Minute),
		"QOUT",
		makeStateJson(time.Now().UTC().Add(-60*time.Hour), "with_followup", `{}`))

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
