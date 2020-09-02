package main

import (
	"context"
	"testing"

	"github.com/confluentinc/confluent-kafka-go/kafka"
	"github.com/jackc/pgx/v4"
	"github.com/stretchr/testify/assert"
)


type StringData struct {
	foo string
}

func (f *StringData) Queue (batch *pgx.Batch) {
	query := "INSERT INTO test (foo) VALUES($1)"
	batch.Queue(query, f.foo)
}

type IntData struct {
	foo int64
}

func (f *IntData) Queue (batch *pgx.Batch) {
	query := "INSERT INTO test (foo) VALUES($1)"
	batch.Queue(query, f.foo)
}

type TestError struct{ msg string }
func (e *TestError) Error() string {
    return e.msg
}

func GoodStringMarshaller(msg *kafka.Message) (Writeable, error){
	return &StringData{"hey"}, nil
}


func ErrorStringMarshaller(msg *kafka.Message) (Writeable, error){
	if string(msg.Value) == "bad" {
		return nil, &TestError{"test"}
	}
	return &StringData{"hey"}, nil
}


func TestPrepWhenAllGood(t *testing.T) {
	data, _ := Prep(GoodStringMarshaller, makeMessages([]string{"foo", "bar"}))
	assert.Equal(t, len(data), 2)
}

func TestPrepWhenOneBadYouGetAnError(t *testing.T) {
	data, err := Prep(ErrorStringMarshaller, makeMessages([]string{"foo", "bad"}))
	assert.Nil(t, data)
	assert.NotNil(t, err)
}


func TestWriteBatchSucceeds(t *testing.T) {

	pool := testPool()
	defer pool.Close()

	sql := `drop table if exists test;
            create table if not exists test(
              foo varchar
           );`

	mustExec(t, pool, sql)

	data := []Writeable{
		&StringData{"bar"},
		&StringData{"baz"},
	}

	err := WriteBatch(pool, data)
	assert.Nil(t, err)

	rows, err := pool.Query(context.Background(), "select * from test")
	handle(err)

	results := []string{}
	for rows.Next() {
		var res string
		_ = rows.Scan(&res)
		results = append(results, res)
	}

	assert.Equal(t, results[0], "bar")
	assert.Equal(t, results[1], "baz")
	assert.Equal(t, len(results), 2)
}

func TestWriteBatchWithFailedLocallyWritesNothing(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	sql := `drop table if exists test;
            create table if not exists test(
              foo varchar
           );`

	mustExec(t, pool, sql)

	data := []Writeable{
		&StringData{"baz"},
		&StringData{"bar"},
		&IntData{1},
	}

	err := WriteBatch(pool, data)
	t.Log(err)
	assert.NotNil(t, err)

	rows, err := pool.Query(context.Background(), "select * from test")
	handle(err)

	results := []string{}
	for rows.Next() {
		var res string
		_ = rows.Scan(&res)
		results = append(results, res)
	}

	assert.Equal(t, len(results), 0)
}

func TestWriteBatchWithFailedOnDBWritesPartially(t *testing.T) {

	pool := testPool()
	defer pool.Close()

	sql := `drop table if exists test;
            create table if not exists test(
              foo int
           );`

	mustExec(t, pool, sql)

	data := []Writeable{
		&IntData{1},
		&IntData{2},
		&StringData{"baz"},
		&IntData{3},
		&IntData{4},
	}

	err := WriteBatch(pool, data)
	assert.NotNil(t, err)

	rows, err := pool.Query(context.Background(), "select * from test")
	handle(err)

	results := []int64{}
	for rows.Next() {
		var res int64
		_ = rows.Scan(&res)
		results = append(results, res)
	}

	assert.Equal(t, len(results), 2)
}
