package main

import (
	"context"
	"time"

	"github.com/confluentinc/confluent-kafka-go/kafka"
	"github.com/jackc/pgx/v4/pgxpool"
)

type Message struct {
	Userid    string    `validate:"required"`
	Timestamp time.Time `validate:"required"`
	Content   []byte    `validate:"required"`
}

func (message *Message) GetRow() []interface{} {
	return []interface{}{
		message.Userid,
		message.Timestamp,
		string(message.Content),
	}
}

type MessageScribbler struct {
	pool *pgxpool.Pool
}

func NewMessageScribbler(pool *pgxpool.Pool) Scribbler {
	return &MessageScribbler{pool}
}

func (s *MessageScribbler) SendBatch(data []Writeable) error {
	values := BatchValues(data)
	fields := []string{"userid", "timestamp", "content"}
	query := SertQuery("INSERT", "messages", fields, len(data))
	query += ` ON CONFLICT(hsh, userid) DO NOTHING`
	_, err := s.pool.Exec(context.Background(), query, values...)
	return err
}

func (s *MessageScribbler) Marshal(msg *kafka.Message) (Writeable, error) {
	return &Message{string(msg.Key), msg.Timestamp, msg.Value}, nil
}
