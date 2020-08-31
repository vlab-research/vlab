package main

import (
	"testing"
	"time"
	"errors"
	"github.com/stretchr/testify/assert"
	"github.com/confluentinc/confluent-kafka-go/kafka"
	"github.com/stretchr/testify/mock"
)

type MockProcessor struct {
	mock.Mock
}

func (m *MockProcessor) Fn (messages []*kafka.Message) error {
	time.Sleep(10*time.Millisecond)
	_ = m.Called(messages)
	return nil
}


func (m *MockProcessor) FnError (messages []*kafka.Message) error {
	_ = m.Called(messages)
	return errors.New("hey")
}


func TestProcessBlocksUntilFunctionsFinish(t *testing.T) {
	messages := make(chan []*kafka.Message)
	go func(){
		defer close(messages)
		for _, _ = range []int{1,2,3} {
			messages <- []*kafka.Message{&kafka.Message{}}
		}
	}()

	m := new(MockProcessor)
	m.On("Fn", []*kafka.Message{&kafka.Message{}})

	errs := process(messages, m.Fn)
	for _ = range errs {}
	m.AssertNumberOfCalls(t, "Fn", 3)
	m.AssertExpectations(t)
}


func TestProcessReturnsChannelWithAllErrors(t *testing.T) {
	messages := make(chan []*kafka.Message)
	go func(){
		defer close(messages)
		for _, _ = range []int{1,2,3} {
			messages <- []*kafka.Message{&kafka.Message{}}
		}
	}()

	m := new(MockProcessor)
	m.On("FnError", []*kafka.Message{&kafka.Message{}})

	errs := process(messages, m.FnError)
	es := []error{}
	for e := range errs {
		es = append(es, e)
	}

	assert.Equal(t, len(es), 3, "returned all 3 errors in channel")
	m.AssertNumberOfCalls(t, "FnError", 3)
	m.AssertExpectations(t)
}
