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

func (s *StateScribbler) SendBatch(values []interface{}) error {
	fields := []string{
		"userid",
		"pageid",
		"updated",
		"current_state",
		"state_json",
	}
	query := SertQuery("UPSERT", "states", fields, values)
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
