package main

import (
	"testing"
	"time"

	"github.com/vlab-research/spine"
	"github.com/go-playground/validator/v10"
	"github.com/stretchr/testify/assert"
)


const (
	stateSql = `
                drop table if exists states;
                drop table if exists facebook_pages;

                create table if not exists facebook_pages(
				  pageid VARCHAR PRIMARY KEY
                 );
                insert into facebook_pages(pageid) values('foo');

                create table if not exists states(
     			  userid VARCHAR NOT NULL,
				  pageid VARCHAR NOT NULL NOT NULL REFERENCES facebook_pages(pageid),
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

	writer := GetWriter(pool, StateMarshaller)
	err := writer.Write(msgs)
	assert.Nil(t, err)

	res := getCol(pool, "states", "state_json->>'token'")
	assert.Equal(t, len(res), 2)

	assert.Equal(t, res[0], "bar")
	assert.Equal(t, res[1], "bar")


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

	writer := GetWriter(pool, StateMarshaller)
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

	writer := GetWriter(pool, StateMarshaller)
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

	writer := GetWriter(pool, StateMarshaller)
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

	writer := GetWriter(pool, StateMarshaller)
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
