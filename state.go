package main

import (
	"encoding/json"

	"github.com/confluentinc/confluent-kafka-go/kafka"
	"github.com/jackc/pgx/v4"
)

type State struct {
	UserID string `json:"userid"  validate:"required"`
	PageID string `json:"pageid"  validate:"required"`
	Updated JSTimestamp `json:"updated"  validate:"required"`
	CurrentState string `json:"current_state"  validate:"required"`
	StateJSON json.RawMessage `json:"state_json"  validate:"required"`
}

func (state *State) Queue(batch *pgx.Batch) {
	fields := []string{
		"userid",
		"pageid",
		"updated",
		"current_state",
		"state_json",
	}
	query := SertQuery("UPSERT", "states", fields)


	batch.Queue(query,
		state.UserID,
		state.PageID,
		state.Updated.Time,
		state.CurrentState,
		state.StateJSON)
}


func StateMarshaller(msg *kafka.Message) (Writeable, error) {
	m := new(State)
	err := json.Unmarshal(msg.Value, m)
	if err != nil {
		return nil, err
	}

	return m, nil
}
