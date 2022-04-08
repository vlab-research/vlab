package main

import (
	"bytes"
	"context"
	"io/ioutil"
	"net/http"
	"testing"

	"github.com/confluentinc/confluent-kafka-go/kafka"
	"github.com/jackc/pgconn"
	"github.com/jackc/pgx/v4/pgxpool"
)

type TestTransport func(req *http.Request) (*http.Response, error)

func (r TestTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	return r(req)
}

func TestClient(statusCode int, body string, err error) *http.Client {
	rt := func(req *http.Request) (*http.Response, error) {
		if err != nil {
			return nil, err
		}
		res := &http.Response{
			StatusCode: statusCode,
			Body:       ioutil.NopCloser(bytes.NewReader([]byte(body))),
		}
		return res, nil
	}

	return &http.Client{Transport: TestTransport(rt)}
}

func makeMessages(vals []string) []*kafka.Message {
	msgs := []*kafka.Message{}
	for _, v := range vals {
		msg := &kafka.Message{}
		msg.Value = []byte(v)
		msgs = append(msgs, msg)
	}

	return msgs
}

func mustExec(t testing.TB, conn *pgxpool.Pool, sql string, arguments ...interface{}) (commandTag pgconn.CommandTag) {
	var err error
	if commandTag, err = conn.Exec(context.Background(), sql, arguments...); err != nil {
		t.Fatalf("Exec unexpectedly failed with %v: %v", sql, err)
	}
	return
}
