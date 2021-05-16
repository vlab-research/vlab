package main

import (
	"github.com/confluentinc/confluent-kafka-go/kafka"
	"github.com/go-playground/validator/v10"
)

type Writeable interface {
	GetRow() []interface{}
}

func BatchValues(data []Writeable) []interface{} {
	values := []interface{}{}
	for _, d := range data {
		for _, r := range d.GetRow() {
			values = append(values, r)
		}
	}

	return values
}

func Prep(fn func(*kafka.Message) (Writeable, error), messages []*kafka.Message) ([]Writeable, error) {
	data := []Writeable{}
	for _, msg := range messages {
		w, err := fn(msg)

		if err != nil {
			// NOTE: will throw at any marhaling problem. Good for now!
			// maybe change this to keep writing and ignore the corrupted data?
			return nil, err

		}
		data = append(data, w)
	}

	return data, nil
}

func Write(v *validator.Validate, scribbler Scribbler, messages []*kafka.Message) error {
	data, err := Prep(scribbler.Marshal, messages)
	if err != nil {
		return err
	}

	for _, d := range data {
		err := v.Struct(d)
		if err != nil {
			return err
		}
	}

	return scribbler.SendBatch(data)
}

type Writer struct {
	validate  *validator.Validate
	scribbler Scribbler
}

type Scribbler interface {
	SendBatch([]Writeable) error
	Marshal(*kafka.Message) (Writeable, error)
}

func (w *Writer) Write(messages []*kafka.Message) error {
	return Write(w.validate, w.scribbler, messages)
}

func GetWriter(scribbler Scribbler) *Writer {
	validate := validator.New()
	return &Writer{validate, scribbler}
}
