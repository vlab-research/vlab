package main

import (
	"context"
	"encoding/json"
	"testing"

	"github.com/confluentinc/confluent-kafka-go/kafka"
	"github.com/jackc/pgx/v4/pgxpool"
	"github.com/stretchr/testify/assert"
)

type StringData struct {
	Foo string `json:"foo" validate:"required"`
}

func (f *StringData) GetRow() []interface{} {
	return []interface{}{f.Foo}
}

type StringScribbler struct {
	pool *pgxpool.Pool
}

func (s *StringScribbler) SendBatch(data []Writeable) error {
	values := BatchValues(data)
	query := SertQuery("INSERT", "test", []string{"foo"}, len(data))
	_, err := s.pool.Exec(context.Background(), query, values...)
	return err
}

func (s *StringScribbler) Marshal(msg *kafka.Message) (Writeable, error) {
	m := new(StringData)
	err := json.Unmarshal(msg.Value, m)
	if err != nil {
		return nil, err
	}

	return m, nil
}

type TestError struct{ msg string }

func (e *TestError) Error() string {
	return e.msg
}

func GoodStringMarshaller(msg *kafka.Message) (Writeable, error) {
	return &StringData{"hey"}, nil
}

func ErrorStringMarshaller(msg *kafka.Message) (Writeable, error) {
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

	msgs := []*kafka.Message{
		{Value: []byte(`{ "foo": "bar"}`)},
		{Value: []byte(`{ "foo": "baz"}`)},
	}

	writer := GetWriter(&StringScribbler{pool})

	err := writer.Write(msgs)
	assert.Nil(t, err)

	rows, err := pool.Query(context.Background(), "select * from test")
	handle(err)

	results := []string{}
	for rows.Next() {
		var res string
		_ = rows.Scan(&res)
		results = append(results, res)
	}

	assert.Equal(t, "bar", results[0])
	assert.Equal(t, "baz", results[1])
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

	msgs := []*kafka.Message{
		{Value: []byte(`{ "foo": "bar"}`)},
		{Value: []byte(`{ "foo": 1}`)},
	}

	writer := GetWriter(&StringScribbler{pool})

	err := writer.Write(msgs)
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
