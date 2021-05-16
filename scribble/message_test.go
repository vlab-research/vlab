package main

import (
	"testing"
	"time"

	"github.com/confluentinc/confluent-kafka-go/kafka"
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

	msgs := []*kafka.Message{
		&kafka.Message{Value: []byte(`{ "foo": "bar "}`), Key: []byte("foo"), Timestamp: time.Now()},
		&kafka.Message{Value: []byte(`{ "bar": "baz "}`), Key: []byte("foo"), Timestamp: time.Now()},
	}

	writer := GetWriter(NewMessageScribbler(pool))
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

	msgs := []*kafka.Message{
		&kafka.Message{Value: []byte(`{ "foo": "bar "}`), Key: []byte("foo"), Timestamp: time.Now()},
		&kafka.Message{Value: []byte(`{ "foo": "bar "}`), Key: []byte("foo"), Timestamp: time.Now()},
	}

	writer := GetWriter(NewMessageScribbler(pool))
	err := writer.Write(msgs)
	assert.Nil(t, err)

	res := getCol(pool, "messages", "content")
	assert.Equal(t, len(res), 1)

	mustExec(t, pool, "drop table messages")
}
