package main 

import (
	"time"

	"github.com/confluentinc/confluent-kafka-go/kafka"
	"github.com/jackc/pgx/v4"
)

type Message struct {
	Userid string `validate:"required"`
	Timestamp time.Time `validate:"required"`
	Content []byte `validate:"required"`
}

func (message *Message) Queue(batch *pgx.Batch) {
	query := `INSERT INTO messages(userid, timestamp, content)
		   values($1, $2, $3)
		   ON CONFLICT(hsh, userid) DO NOTHING`

	batch.Queue(query,
		message.Userid,
		message.Timestamp,
		string(message.Content))
}

func MessageMarshaller(msg *kafka.Message) (Writeable, error) {
	return &Message{string(msg.Key), msg.Timestamp, msg.Value}, nil
}
