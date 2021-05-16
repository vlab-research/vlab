package main

import (
	"context"
	"encoding/json"

	"github.com/confluentinc/confluent-kafka-go/kafka"
	"github.com/jackc/pgx/v4/pgxpool"
)

type State struct {
	UserID       string          `json:"userid"  validate:"required"`
	PageID       string          `json:"pageid"  validate:"required"`
	Updated      JSTimestamp     `json:"updated"  validate:"required"`
	CurrentState string          `json:"current_state"  validate:"required"`
	StateJSON    json.RawMessage `json:"state_json"  validate:"required"`
}

func (state *State) GetRow() []interface{} {
	return []interface{}{
		state.UserID,
		state.PageID,
		state.Updated.Time,
		state.CurrentState,
		state.StateJSON,
	}
}

type StateScribbler struct {
	pool *pgxpool.Pool
}

func NewStateScribbler(pool *pgxpool.Pool) Scribbler {
	return &StateScribbler{pool}
}

func DedupStates(data []Writeable) []Writeable {
	dataMap := map[string]*State{}
	for _, d := range data {
		state, ok := d.(*State)
		if !ok {
			panic("Cannot decode state Writeable as State!")
		}
		dataMap[state.UserID] = state
	}

	data = []Writeable{}
	for _, d := range dataMap {
		data = append(data, d)
	}

	return data
}

func (s *StateScribbler) SendBatch(data []Writeable) error {
	data = DedupStates(data)
	values := BatchValues(data)
	fields := []string{
		"userid",
		"pageid",
		"updated",
		"current_state",
		"state_json",
	}
	query := SertQuery("UPSERT", "states", fields, len(data))
	_, err := s.pool.Exec(context.Background(), query, values...)
	return err
}

func (s *StateScribbler) Marshal(msg *kafka.Message) (Writeable, error) {
	m := new(State)
	err := json.Unmarshal(msg.Value, m)
	if err != nil {
		return nil, err
	}

	return m, nil
}
