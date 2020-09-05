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

type TestConsumer struct {
	Messages []*kafka.Message
	Commits int
	commitError bool
}

func (c *TestConsumer) ReadMessage(d time.Duration) (*kafka.Message, error) {
	if len(c.Messages) == 0 {
		return nil, kafka.NewError(kafka.ErrTimedOut, "test", false)
	}

	head := c.Messages[0]
	c.Messages = c.Messages[1:]
	return head, nil
}

func (c *TestConsumer) Commit() ([]kafka.TopicPartition, error) {
	c.Commits += 1
	if c.commitError {
		return nil, &TestError{"foo"}
	}
	return []kafka.TopicPartition{}, nil
}

func TestSideEffectReadPartial(t *testing.T) {
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

	c := &TestConsumer{Messages: msgs, Commits: 0}
	consumer := KafkaConsumer{c, time.Second, 1, 1}
	count := 0
	fn := func([]*kafka.Message) error { 
		count += 1
		return nil 
	}

	errs := make(chan error)
	consumer.SideEffect(fn, errs)
	assert.Equal(t, c.Commits, 1)
	assert.Equal(t, len(c.Messages), 1)
}

func TestSideEffectErrorsDoesntCommitBeforeHandlingError(t *testing.T) {
	msgs := makeMessages([]string{
		`{"userid": "bar",
          "pageid": "foo",
          "updated": 1598706047838,
          "current_state": "QOUT",
          "state_json": { "token": "bar", "state": "QOUT", "tokens": ["foo"]}}`,
	})

	c := &TestConsumer{Messages: msgs, Commits: 0}
	consumer := KafkaConsumer{c, time.Second, 1, 1}
	count := 0
	fn := func([]*kafka.Message) error { 
		count += 1
		return errors.New("test")
	}

	done := make(chan bool)
	errs := make(chan error)
	go func(){
		for _ = range errs {
			assert.Equal(t, 0, c.Commits)
			close(done)
		}
	}()
	consumer.SideEffect(fn, errs)

	<- done
}


func TestSideEffectOutputsCommitErrorOnErrorChannel(t *testing.T) {
	msgs := makeMessages([]string{
		`{"userid": "bar",
          "pageid": "foo",
          "updated": 1598706047838,
          "current_state": "QOUT",
          "state_json": { "token": "bar", "state": "QOUT", "tokens": ["foo"]}}`,
	})

	c := &TestConsumer{Messages: msgs, Commits: 0, commitError: true}
	consumer := KafkaConsumer{c, time.Second, 1, 1}
	count := 0
	fn := func([]*kafka.Message) error { 
		count += 1
		return nil
	}

	done := make(chan bool)
	errs := make(chan error)
	go func(){
		for e := range errs {
			t.Log(e)
			_, ok := e.(*TestError)
			assert.Equal(t, true, ok)
			close(done)
		}
	}()
	consumer.SideEffect(fn, errs)

	<- done
}

func TestSideEffectReadAllOutstanding(t *testing.T) {
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

	c := &TestConsumer{Messages: msgs, Commits: 0}
	consumer := KafkaConsumer{c, time.Second, 3, 3}
	count := 0
	fn := func([]*kafka.Message) error { 
		count += 1
		return nil 
	}

	errs := make(chan error)
	consumer.SideEffect(fn, errs)
	assert.Equal(t, 1, c.Commits)
	assert.Equal(t, 0, len(c.Messages))
}
