package main

import (
	"context"

	"github.com/go-playground/validator/v10"
	"github.com/jackc/pgx/v4/pgxpool"
	"github.com/confluentinc/confluent-kafka-go/kafka"
	"github.com/jackc/pgx/v4"
)

type Writeable interface {
	Queue(*pgx.Batch)
}
type MarshalWriteable func(*kafka.Message) (Writeable, error)

func Write(v *validator.Validate, pool *pgxpool.Pool, fn MarshalWriteable, messages []*kafka.Message) error {
	data, err := Prep(fn, messages)
	if err != nil {
		return err
	}

	for _, d := range data {
		err := v.Struct(d)
		if err != nil {
			return err
		}
	}

	return WriteBatch(pool, data)
}

func Prep(fn MarshalWriteable, messages []*kafka.Message) ([]Writeable, error) {
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

func WriteBatch(pool *pgxpool.Pool, data []Writeable) error {
	// TODO: this only returns a single error
	// but an error could occur on any insert
	batch := &pgx.Batch{}
	for _, d := range data {
		d.Queue(batch)
	}
	br := pool.SendBatch(context.Background(), batch)
	return br.Close() // contains any error in batchresults
}


type Writer struct {
	pool *pgxpool.Pool
	validate *validator.Validate
	fn MarshalWriteable
}

func GetWriter(pool *pgxpool.Pool, fn MarshalWriteable) *Writer {
	validate := validator.New()
	return &Writer{pool, validate, fn}
}

func (w *Writer) Write(messages []*kafka.Message) error {
	return Write(w.validate, w.pool, w.fn, messages)
}
