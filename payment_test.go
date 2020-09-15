package main

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

const (
	paymentSql = `
            drop table if exists payments;
            create table if not exists payments(
			  userid VARCHAR NOT NULL,
			  pageid VARCHAR NOT NULL,
			  timestamp TIMESTAMPTZ NOT NULL,
			  provider VARCHAR NOT NULL,
			  details JSON NOT NULL,
              results JSON,
			  PRIMARY KEY (userid, pageid, timestamp)
           );`
)

func TestPaymentWriterWritesGoodData(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, paymentSql)

	msgs := makeMessages([]string{
		`{
          "userid": "foo",
          "pageid": "baz",
          "provider": "qux",
          "timestamp": 1599039840517,
          "details": {"key":"value"}}`,
		`{
          "userid": "bar",
          "pageid": "baz",
          "provider": "qux",
          "timestamp": 1599039840517,
          "details": {"key":"value"}}`,
	})

	writer := GetWriter(pool, PaymentMarshaller)
	err := writer.Write(msgs)
	assert.Nil(t, err)

	res := getCol(pool, "payments", "userid")
	assert.Equal(t, 2, len(res))
	assert.Equal(t, "bar", res[0])
	assert.Equal(t, "foo", res[1])

	mustExec(t, pool, "drop table payments")
}


func TestPaymentIgnoresRepeatedData(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, paymentSql)

	msgs := makeMessages([]string{
		`{
          "userid": "foo",
          "pageid": "baz",
          "provider": "qux",
          "timestamp": 1599039840517,
          "details": {"key":"value"}}`,
		`{
          "userid": "foo",
          "pageid": "baz",
          "provider": "qux",
          "timestamp": 1599039840517,
          "details": {"key":"value"}}`,
		`{
          "userid": "bar",
          "pageid": "baz",
          "provider": "qux",
          "timestamp": 1599039840517,
          "details": {"key":"value"}}`,
	})

	writer := GetWriter(pool, PaymentMarshaller)
	err := writer.Write(msgs)
	assert.Nil(t, err)

	res := getCol(pool, "payments", "userid")
	assert.Equal(t, 2, len(res))
	assert.Equal(t, "bar", res[0])
	assert.Equal(t, "foo", res[1])

	mustExec(t, pool, "drop table payments")
}



func TestPaymentDoesNotWriteAnythingOnBadData(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, paymentSql)

	msgs := makeMessages([]string{
		`{
          "userid": "foo",
          "pageid": "baz",
          "timestamp": 1599039840517,
          "details": {"key":"value"}}`,
		`{
          "userid": "foo",
          "pageid": "baz",
          "provider": "qux",
          "timestamp": 1599039840517,
          "details": {"key":"value"}}`,
		`{
          "userid": "bar",
          "pageid": "baz",
          "provider": "qux",
          "timestamp": 1599039840517,
          "details": {"key":"value"}}`,
	})

	writer := GetWriter(pool, PaymentMarshaller)
	err := writer.Write(msgs)
	assert.NotNil(t, err)

	res := getCol(pool, "payments", "userid")
	assert.Equal(t, 0, len(res))

	mustExec(t, pool, "drop table payments")
}
