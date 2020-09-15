package main

import (
	"encoding/json"

	"github.com/confluentinc/confluent-kafka-go/kafka"
	"github.com/jackc/pgx/v4"
)

type Payment struct {
	Userid string `json:"userid" validate:"required"`
	Pageid string `json:"pageid" validate:"required"`
	Timestamp *JSTimestamp `json:"timestamp" validate:"required"`
	Provider string `json:"provider" validate:"required"`
	Details json.RawMessage `json:"details" validate:"required"`
}

func (p *Payment) Queue(batch *pgx.Batch) {
	query := SertQuery("INSERT", "payments", []string{
		"userid",
		"pageid",
		"timestamp",
		"provider",
		"details",
	})
	query += " ON CONFLICT(id) DO NOTHING"

	batch.Queue(query,
		p.Userid,
		p.Pageid,
		p.Timestamp.Time,
		p.Provider,
		p.Details,
	)
}

func PaymentMarshaller(msg *kafka.Message) (Writeable, error) {
	m := new(Payment)
	err := json.Unmarshal(msg.Value, m)
	if err != nil {
		return nil, err
	}
	return m, nil
}
