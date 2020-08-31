package main

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestMessageWriterWritesGoodData(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	sql := `drop table if exists messages;
            create table if not exists messages(
			  userid VARCHAR NOT NULL,
			  timestamp TIMESTAMPTZ NOT NULL,
			  content VARCHAR NOT NULL,
              hsh INT AS (fnv64a(content)) STORED NOT NULL,
			  PRIMARY KEY (hsh, userid)
           );`

	mustExec(t, pool, sql)

	msgs := makeMessages([]string{
		`{"userid": "bar",
          "timestamp": 1598706047838,
          "content": { "token": "bar", "tokens": ["foo"]}}`,
		`{"userid": "baz",
          "timestamp": 1598706047838,
          "content": { "token": "bar", "tokens": ["foo"]}}`,
	})

	writer := GetWriter(pool, MessageMarshaller)
	err := writer.Write(msgs)
	assert.Nil(t, err)

	res := getCol(pool, "messages", "content")
	assert.Equal(t, len(res), 2)

	mustExec(t, pool, "drop table messages")
}

func TestMessageWriterDoesNotThrowOnDuplicateMessage(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	sql := `drop table if exists messages;
            create table if not exists messages(
			  userid VARCHAR NOT NULL,
			  timestamp TIMESTAMPTZ NOT NULL,
			  content VARCHAR NOT NULL,
              hsh INT AS (fnv64a(content)) STORED NOT NULL,
			  PRIMARY KEY (hsh, userid)
           );`

	mustExec(t, pool, sql)

	msgs := makeMessages([]string{
		`{"userid": "bar",
          "timestamp": 1598706047838,
          "content": { "token": "bar", "tokens": ["foo"]}}`,
		`{"userid": "bar",
          "timestamp": 1598706047838,
          "content": { "token": "bar", "tokens": ["foo"]}}`,
	})

	writer := GetWriter(pool, MessageMarshaller)
	err := writer.Write(msgs)
	assert.Nil(t, err)

	res := getCol(pool, "messages", "content")
	assert.Equal(t, len(res), 1)

	mustExec(t, pool, "drop table messages")
}
