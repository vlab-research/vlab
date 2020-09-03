package main

import (
	"testing"
	"context"

	"github.com/stretchr/testify/assert"
)

const (
	responseSql = `drop table if exists responses;
            create table if not exists responses(
			  parent_shortcode VARCHAR NOT NULL,
			  surveyid UUID NOT NULL,
			  shortcode VARCHAR NOT NULL,
			  flowid INT NOT NULL,
			  userid VARCHAR NOT NULL,
			  pageid VARCHAR,
			  question_ref VARCHAR NOT NULL,
			  question_idx INT NOT NULL,
			  question_text VARCHAR NOT NULL,
			  response VARCHAR NOT NULL,
			  seed INT NOT NULL,
			  timestamp TIMESTAMPTZ NOT NULL,
              metadata JSONB,
              CONSTRAINT "valid_metadata" CHECK (json_typeof(metadata) = 'object'),
			  PRIMARY KEY (userid, timestamp, question_ref)
           );`
)

func TestResponseWriterWritesGoodData(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, responseSql)

	msgs := makeMessages([]string{
		`{"parent_surveyid":"d6c21c81-fcd0-4aa4-8975-8584d8bdb820",
          "parent_shortcode":"baz",
          "surveyid":"d6c21c81-fcd0-4aa4-8975-8584d8bdb820",
          "shortcode":"baz",
          "flowid":1,
          "userid":"foo",
          "pageid": "baz",
          "question_ref":"bar",
          "question_idx":1,
          "question_text":"foobar",
          "response":"LOL",
          "seed":858044518,
          "metadata": {"foo":"bar","seed": 8978437},
          "timestamp":1599039840517}`,
		`{"parent_surveyid":"d6c21c81-fcd0-4aa4-8975-8584d8bdb820",
          "parent_shortcode":"baz",
          "surveyid":"d6c21c81-fcd0-4aa4-8975-8584d8bdb820",
          "shortcode":"baz",
          "flowid":1,
          "userid":"bar",
          "pageid": "baz",
          "question_ref":"bar",
          "question_idx":1,
          "question_text":"foobar",
          "response":"LOL",
          "seed":858044518,
          "metadata": {"foo":"bar","seed": 8978437},
          "timestamp":1599039840517}`,
	})

	writer := GetWriter(pool, ResponseMarshaller)
	err := writer.Write(msgs)
	assert.Nil(t, err)

	res := getCol(pool, "responses", "userid")
	assert.Equal(t, 2, len(res))
	assert.Equal(t, "bar", res[0])
	assert.Equal(t, "foo", res[1])

	res = getCol(pool, "responses", "metadata->>'foo'")
	assert.Equal(t, 2, len(res))
	assert.Equal(t, "bar", res[0])
	assert.Equal(t, "bar", res[1])


	mustExec(t, pool, "drop table responses")
}


func TestResponseWriterWritesNullPageIdIfNone(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, responseSql)

	msgs := makeMessages([]string{
		`{"parent_surveyid":"d6c21c81-fcd0-4aa4-8975-8584d8bdb820",
          "parent_shortcode":"baz",
          "surveyid":"d6c21c81-fcd0-4aa4-8975-8584d8bdb820",
          "shortcode":"baz",
          "flowid":1,
          "userid":"foo",
          "question_ref":"bar",
          "question_idx":1,
          "question_text":"foobar",
          "response":"LOL",
          "seed":858044518,
          "metadata": {"foo":"bar","seed": 8978437},
          "timestamp":1599039840517}`,
	})

	writer := GetWriter(pool, ResponseMarshaller)
	err := writer.Write(msgs)
	assert.Nil(t, err)

	rows, err := pool.Query(context.Background(), "select pageid from responses where pageid is null")
	res := rowStrings(rows)
	assert.Equal(t, 1, len(res))

	mustExec(t, pool, "drop table responses")
}


func TestResponseWriterWritesPageIdIfExists(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, responseSql)

	msgs := makeMessages([]string{
		`{"parent_surveyid":"d6c21c81-fcd0-4aa4-8975-8584d8bdb820",
          "parent_shortcode":"baz",
          "surveyid":"d6c21c81-fcd0-4aa4-8975-8584d8bdb820",
          "shortcode":"baz",
          "flowid":1,
          "userid":"foo",
          "pageid": "baz",
          "question_ref":"bar",
          "question_idx":1,
          "question_text":"foobar",
          "response":"LOL",
          "seed":858044518,
          "metadata": {"foo":"bar","seed": 8978437},
          "timestamp":1599039840517}`,
	})

	writer := GetWriter(pool, ResponseMarshaller)
	err := writer.Write(msgs)
	assert.Nil(t, err)

	res := getCol(pool, "responses", "pageid")
	assert.Equal(t, 1, len(res))
	assert.Equal(t, "baz", res[0])

	mustExec(t, pool, "drop table responses")
}



func TestResponseWriterHandlesMixedResponseAndShortCodeTypes(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, responseSql)

	msgs := makeMessages([]string{
		`{"parent_surveyid":"d6c21c81-fcd0-4aa4-8975-8584d8bdb820",
          "parent_shortcode":"baz",
          "surveyid":"d6c21c81-fcd0-4aa4-8975-8584d8bdb820",
          "shortcode":"baz",
          "flowid":1,
          "userid":"foo",
          "pageid": "baz",
          "question_ref":"bar",
          "question_idx":1,
          "question_text":"foobar",
          "response":true,
          "seed":858044518,
          "metadata": {"foo":"bar","seed": 8978437},
          "timestamp":1599039840517}`,
		`{"parent_surveyid":"d6c21c81-fcd0-4aa4-8975-8584d8bdb820",
          "parent_shortcode":"baz",
          "surveyid":"d6c21c81-fcd0-4aa4-8975-8584d8bdb820",
          "shortcode":"baz",
          "flowid":1,
          "userid":"foo",
          "pageid": "baz",
          "question_ref":"baz",
          "question_idx":1,
          "question_text":"foobar",
          "response":"yes",
          "seed":858044518,
          "metadata": {"foo":"bar","seed": 8978437},
          "timestamp":1599039840517}`,
		`{"parent_surveyid":"d6c21c81-fcd0-4aa4-8975-8584d8bdb820",
          "parent_shortcode":123,
          "surveyid":"d6c21c81-fcd0-4aa4-8975-8584d8bdb820",
          "shortcode":123,
          "flowid":1,
          "userid":"foo",
          "pageid": "baz",
          "question_ref":"qux",
          "question_idx":1,
          "question_text":"foobar",
          "response":25,
          "seed":858044518,
          "metadata": {"foo":"bar","seed": 8978437},
          "timestamp":1599039840517}`,
	})

	writer := GetWriter(pool, ResponseMarshaller)
	err := writer.Write(msgs)
	assert.Nil(t, err)

	res := getCol(pool, "responses", "response")
	assert.Equal(t, 3, len(res))
	assert.Equal(t, "true", res[0])
	assert.Equal(t, "yes", res[1])
	assert.Equal(t, "25", res[2])

	res = getCol(pool, "responses", "shortcode")
	assert.Equal(t, 3, len(res))
	assert.Equal(t, "baz", res[0])
	assert.Equal(t, "123", res[2])

	mustExec(t, pool, "drop table responses")
}

func TestResponseWriterFailsOnMissingData(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, responseSql)

	msgs := makeMessages([]string{
		`{"parent_surveyid":"d6c21c81-fcd0-4aa4-8975-8584d8bdb820",
          "parent_shortcode":"baz",
          "surveyid":"d6c21c81-fcd0-4aa4-8975-8584d8bdb820",
          "shortcode":"baz",
          "flowid":1,
          "userid":"foo",
"pageid": "baz",
          "question_ref":"bar",
          "question_idx":1,
          "question_text":"foobar",
          "seed":858044518,
          "metadata": {"foo":"bar","seed": 8978437},
          "timestamp":1599039840517}`,
	})

	writer := GetWriter(pool, ResponseMarshaller)
	err := writer.Write(msgs)
	assert.NotNil(t, err)

	res := getCol(pool, "responses", "userid")
	assert.Equal(t, 0, len(res))
	mustExec(t, pool, "drop table responses")
}


func TestResponseWriterFailsOnMissingMetadata(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, responseSql)

	msgs := makeMessages([]string{
		`{"parent_surveyid":"d6c21c81-fcd0-4aa4-8975-8584d8bdb820",
          "parent_shortcode":"baz",
          "surveyid":"d6c21c81-fcd0-4aa4-8975-8584d8bdb820",
          "shortcode":"baz",
          "flowid":1,
          "userid":"foo",
          "pageid": "baz",
          "question_ref":"bar",
          "question_idx":1,
          "question_text":"foobar",
          "response":"LOL",
          "seed":858044518,
          "timestamp":1599039840517}`,
	})

	writer := GetWriter(pool, ResponseMarshaller)
	err := writer.Write(msgs)
	assert.NotNil(t, err)

	res := getCol(pool, "responses", "userid")
	assert.Equal(t, 0, len(res))
	mustExec(t, pool, "drop table responses")
}


func TestResponseWriterFailsIfMetadataFormatedPoorly(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, responseSql)

	msgs := makeMessages([]string{
		`{"parent_surveyid":"d6c21c81-fcd0-4aa4-8975-8584d8bdb820",
          "parent_shortcode":"baz",
          "surveyid":"d6c21c81-fcd0-4aa4-8975-8584d8bdb820",
          "shortcode":"baz",
          "flowid":1,
          "userid":"foo",
          "pageid": "baz",
          "question_ref":"bar",
          "question_idx":1,
          "question_text":"foobar",
          "response":"LOL",
          "seed":858044518,
          "metadata":"{\"foo\":\"bar\",\"startTime\":1599039840517}",
          "timestamp":1599039840517}`,
	})

	writer := GetWriter(pool, ResponseMarshaller)
	err := writer.Write(msgs)
	assert.NotNil(t, err)

	res := getCol(pool, "responses", "metadata->>'foo'")
	assert.Equal(t, 0, len(res))

	mustExec(t, pool, "drop table responses")
}


func TestResponseWriterSucceedsIfMetadataEmpty(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, responseSql)

	msgs := makeMessages([]string{
		`{"parent_surveyid":"d6c21c81-fcd0-4aa4-8975-8584d8bdb820",
          "parent_shortcode":"baz",
          "surveyid":"d6c21c81-fcd0-4aa4-8975-8584d8bdb820",
          "shortcode":"baz",
          "flowid":1,
          "userid":"foo",
          "pageid": "baz",
          "question_ref":"bar",
          "question_idx":1,
          "question_text":"foobar",
          "response":"LOL",
          "seed":858044518,
          "metadata":{},
          "timestamp":1599039840517}`,
	})

	writer := GetWriter(pool, ResponseMarshaller)
	err := writer.Write(msgs)
	assert.Nil(t, err)

	res := getCol(pool, "responses", "metadata->>'foo'")
	assert.Equal(t, 1, len(res))

	mustExec(t, pool, "drop table responses")
}

func TestResponseWriterIgnoresRepeatMessages(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, responseSql)

	msgs := makeMessages([]string{
		`{"parent_surveyid":"d6c21c81-fcd0-4aa4-8975-8584d8bdb820",
          "parent_shortcode":"baz",
          "surveyid":"d6c21c81-fcd0-4aa4-8975-8584d8bdb820",
          "shortcode":"baz",
          "flowid":1,
          "userid":"foo",
          "pageid": "baz",
          "question_ref":"bar",
          "question_idx":1,
          "question_text":"foobar",
          "response":"LOL",
          "seed":858044518,
          "metadata": {"foo":"bar","seed": 8978437},
          "timestamp":1599039840517}`,
		`{"parent_surveyid":"d6c21c81-fcd0-4aa4-8975-8584d8bdb820",
          "parent_shortcode":"baz",
          "surveyid":"d6c21c81-fcd0-4aa4-8975-8584d8bdb820",
          "shortcode":"baz",
          "flowid":1,
          "userid":"foo",
          "pageid": "baz",
          "question_ref":"bar",
          "question_idx":1,
          "question_text":"foobar",
          "response":"LOL",
          "seed":858044518,
          "metadata": {"foo":"bar","seed": 8978437},
          "timestamp":1599039840517}`,
	})

	writer := GetWriter(pool, ResponseMarshaller)
	err := writer.Write(msgs)
	assert.Nil(t, err)

	res := getCol(pool, "responses", "userid")
	assert.Equal(t, 1, len(res))
	assert.Equal(t, "foo", res[0])

	mustExec(t, pool, "drop table responses")
}
