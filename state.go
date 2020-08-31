package main

import (
	"encoding/json"

	"github.com/jackc/pgx/v4"
)

type State struct {
	UserID string `json:"userid"  validate:"required"`
	PageID string `json:"pageid"  validate:"required"`
	Updated int64 `json:"updated"  validate:"required"`
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
	query := UpsertQuery("states", fields)

	batch.Queue(query,
		state.UserID,
		state.PageID,
		ParseTimestamp(state.Updated),
		state.CurrentState,
		state.StateJSON)
}


func StateMarshaller(b []byte) (Writeable, error) {
	state := new(State)
	err := json.Unmarshal(b, state)
	if err != nil {
		return nil, err
	}

	return state, nil
}
