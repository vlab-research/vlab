package main

import (
	"context"
	"testing"
	"time"

	"github.com/go-playground/validator/v10"
	"github.com/stretchr/testify/assert"
	"github.com/vlab-research/spine"
)

const (
	stateSql = `
                drop table if exists states;
                drop table if exists credentials;

                create table if not exists credentials(
		    entity VARCHAR NOT NULL,
		    key VARCHAR NOT NULL UNIQUE,
		    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
		    details JSONB NOT NULL,
		    facebook_page_id VARCHAR AS (CASE WHEN entity = 'facebook_page' THEN details->>'id' ELSE NULL END) STORED,
		    UNIQUE(entity, key),
                    UNIQUE(facebook_page_id)
                );

                insert into credentials(entity, key, details) values('facebook_page', 'foo', '{"id": "foo"}');

                create table if not exists states(
     			  userid VARCHAR NOT NULL,
			  pageid VARCHAR NOT NULL NOT NULL REFERENCES credentials(facebook_page_id),
			  updated TIMESTAMPTZ NOT NULL,
			  current_state VARCHAR NOT NULL,
			  state_json JSON NOT NULL,
                  CONSTRAINT "valid_state_json" CHECK (state_json ? 'state'),
				  PRIMARY KEY (userid, pageid)
                );`
)

func TestStateWriterWritesGoodData(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, stateSql)
	mustExec(t, pool, stateSql)

	msgs := makeMessages([]string{
		`{"userid": "bar",
          "pageid": "foo",
          "updated": 1598706047838,
          "current_state": "QOUT",
          "state_json": { "token": "bar", "state": "QOUT", "tokens": ["foo"]}}`,
		`{"userid": "baz",
          "pageid": "foo",
          "updated": 1598706047838,
          "current_state": "RESPONDING",
          "state_json": { "token": "bar", "state": "QOUT", "tokens": ["foo"]}}`,
	})

	writer := GetWriter(NewStateScribbler(pool))
	err := writer.Write(msgs)
	assert.Nil(t, err)

	res := getCol(pool, "states", "state_json->>'token'")
	assert.Equal(t, len(res), 2)

	assert.Equal(t, "bar", *res[0])
	assert.Equal(t, "bar", *res[1])

	mustExec(t, pool, "drop table states")
}

func TestStateWriterOverwritesOnePersonsState(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, stateSql)
	mustExec(t, pool, stateSql)

	msgs := makeMessages([]string{
		`{"userid": "bar",
          "pageid": "foo",
          "updated": 1598706047838,
          "current_state": "QOUT",
          "state_json": { "token": "bar", "state": "QOUT", "tokens": ["foo"]}}`,
		`{"userid": "bar",
          "pageid": "foo",
          "updated": 1598706047838,
          "current_state": "RESPONDING",
          "state_json": { "token": "bar", "state": "QOUT", "tokens": ["foo"]}}`,
	})

	writer := GetWriter(NewStateScribbler(pool))
	err := writer.Write(msgs)
	assert.Nil(t, err)

	res := getCol(pool, "states", "current_state")
	assert.Equal(t, len(res), 1)

	assert.Equal(t, "RESPONDING", *res[0])

	mustExec(t, pool, "drop table states")
}

func TestStateWriterOverwritesOnePersonsStateIgnoresUpdatedTimeOverwritesWithLatest(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, stateSql)
	mustExec(t, pool, stateSql)

	msgs := makeMessages([]string{
		`{"userid": "bar",
          "pageid": "foo",
          "updated": 1598706047838,
          "current_state": "QOUT",
          "state_json": { "token": "bar", "state": "QOUT", "tokens": ["foo"]}}`,
		`{"userid": "bar",
          "pageid": "foo",
          "updated": 1598706035000,
          "current_state": "RESPONDING",
          "state_json": { "token": "bar", "state": "QOUT", "tokens": ["foo"]}}`,
	})

	writer := GetWriter(NewStateScribbler(pool))
	err := writer.Write(msgs)
	assert.Nil(t, err)

	rows, err := pool.Query(context.Background(), "select updated from states")
	assert.Nil(t, err)

	for rows.Next() {
		col := new(time.Time)
		err = rows.Scan(&col)
		assert.Nil(t, err)
		assert.Equal(t, int64(1598706035), col.Unix())
	}

	mustExec(t, pool, "drop table states")
}

func TestStateWriterFailsOnBadDataInOneRecordValidationHandler(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, stateSql)

	msgs := makeMessages([]string{
		`{"userid": "bar",
          "pageid": "foo",
          "updated": 1598706047838,
          "state_json": { "token": "bar", "state": "QOUT", "tokens": ["foo"]}}`,

		`{"userid": "baz",
          "pageid": "foo",
          "updated": 1598706047838,
          "current_state": "RESPONDING",
          "state_json": { "token": "bar", "state": "QOUT", "tokens": ["foo"]}}`,
	})

	writer := GetWriter(NewStateScribbler(pool))
	err := writer.Write(msgs)
	assert.NotNil(t, err)

	handled, _ := ValidationHandler(err)
	assert.True(t, handled)

	if e, ok := err.(validator.ValidationErrors); ok {
		t.Log(e)
	}

	res := getCol(pool, "states", "state_json->>'token'")
	assert.Equal(t, len(res), 0)

	mustExec(t, pool, "drop table states")
}

func TestStateWriterFailsOnMissingState(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, stateSql)

	msgs := makeMessages([]string{
		`{"userid": "baz",
          "pageid": "foo",
          "updated": 1598706047838,
          "current_state": "RESPONDING",
          "state_json": {}}`,
	})

	writer := GetWriter(NewStateScribbler(pool))
	err := writer.Write(msgs)
	assert.NotNil(t, err)

	handled, _ := CheckConstraintHandler(err)
	assert.True(t, handled)

	res := getCol(pool, "states", "state_json->>'token'")
	assert.Equal(t, len(res), 0)

	mustExec(t, pool, "drop table states")
}

func TestStateWriterFailsStateViolatesFacebookPageConstraintHandledByForeignKeyHandler(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, stateSql)

	msgs := makeMessages([]string{
		`{"userid": "baz",
          "pageid": "notapage",
          "updated": 1598706047838,
          "current_state": "RESPONDING",
          "state_json": { "token": "bar", "state": "QOUT", "tokens": ["foo"]}}`,
	})

	writer := GetWriter(NewStateScribbler(pool))
	err := writer.Write(msgs)
	assert.NotNil(t, err)

	// TODO: this isn't a unit test, testing foreignkeyhandlers too
	handled, _ := ForeignKeyHandler(err)
	assert.True(t, handled)

	res := getCol(pool, "states", "state_json->>'token'")
	assert.Equal(t, len(res), 0)

	mustExec(t, pool, "drop table states")
}

func TestStateWriterWithHandlersIntegration(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, stateSql)

	msgs := makeMessages([]string{
		`{"userid": "bar",
          "pageid": "foo",
          "updated": 1598706047838,
          "state_json": { "token": "bar", "state": "QOUT", "tokens": ["foo"]}}`,
		`{"userid": "baz",
          "pageid": "foo",
          "updated": 1598706047838,
          "current_state": "RESPONDING",
          "state_json": { "token": "baz", "state": "QOUT", "tokens": ["foo"]}}`,
		`{"userid": "baz",
          "pageid": "notapage",
          "updated": 1598706047838,
          "current_state": "RESPONDING",
          "state_json": { "token": "qux", "state": "QOUT", "tokens": ["foo"]}}`,
	})

	writer := GetWriter(NewStateScribbler(pool))
	c := &spine.TestConsumer{Messages: msgs, Commits: 0}

	consumer := spine.KafkaConsumer{c, time.Second, 3, 1}

	errs := make(chan error)

	mainErrors := HandleErrors(errs, getHandlers(&Config{Handlers: "validation,foreignkey"}))
	go func() {
		for e := range mainErrors {
			t.Errorf("Should not have any errors, had error: %v", e)
		}
	}()

	consumer.SideEffect(writer.Write, errs)
	res := getCol(pool, "states", "state_json->>'token'")
	assert.Equal(t, 1, len(res))

	mustExec(t, pool, "drop table states")
}
