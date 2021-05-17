package main

import (
	"bytes"
	"fmt"
	"net/http"

	"io/ioutil"

	"github.com/confluentinc/confluent-kafka-go/kafka"
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

type MockErrorProvider struct {
	count int
}

func (p *MockErrorProvider) Payout(pe *PaymentEvent) (*Result, error) {
	p.count++
	return nil, fmt.Errorf("mock error")
}
