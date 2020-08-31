package main 

import (
	"encoding/json"

	"github.com/jackc/pgx/v4"
)


type Message struct {
	Userid string `json:"userid"  validate:"required"`
	Timestamp int64 `json:"timestamp"  validate:"required"`
	Content json.RawMessage `json:"content"  validate:"required"`
}

func (message *Message) Queue(batch *pgx.Batch) {
	query := `INSERT INTO messages(userid, timestamp, content)
		   values($1, $2, $3)
		   ON CONFLICT(hsh, userid) DO NOTHING`

	batch.Queue(query,
		message.Userid,
		ParseTimestamp(message.Timestamp),
		string(message.Content))
}


func MessageMarshaller(b []byte) (Writeable, error) {
	marshalled := new(Message)
	err := json.Unmarshal(b, marshalled)
	if err != nil {
		return nil, err
	}

	return marshalled, nil
}
