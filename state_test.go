package main

import (
	"testing"

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
                  CONSTRAINT "valid_state_json" CHECK (state_json ? 'state'),
				  PRIMARY KEY (userid, pageid)
           );`
)

func TestStateWriterWritesGoodData(t *testing.T) {
	pool := testPool()
	defer pool.Close()

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

func TestStateWriterFailsOnBadDataInOneRecord(t *testing.T) {
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

	t.Log(msgs)

	writer := GetWriter(pool, StateMarshaller)
	err := writer.Write(msgs)
	assert.NotNil(t, err)

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

	t.Log(msgs)

	writer := GetWriter(pool, StateMarshaller)
	err := writer.Write(msgs)
	assert.NotNil(t, err)

	res := getCol(pool, "states", "state_json->>'token'")
	assert.Equal(t, len(res), 0)

	mustExec(t, pool, "drop table states")
}
