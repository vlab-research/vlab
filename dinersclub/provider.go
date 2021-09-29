package main

import (
	"encoding/json"
	"time"

	"github.com/jackc/pgx/v4/pgxpool"
)

type JSTimestamp time.Time

func (t *JSTimestamp) UnmarshalJSON(b []byte) error {
	var i int64
	err := json.Unmarshal(b, &i)
	if err != nil {
		return err
	}
	*t = JSTimestamp(time.Unix(0, i*1000000).UTC())
	return nil
}

// Add id for payment??? hash of userid/pageid/timestamp? question ref? id field in description?
type PaymentEvent struct {
	Userid    string           `json:"userid" validate:"required"`
	Pageid    string           `json:"pageid" validate:"required"`
	Timestamp *JSTimestamp     `json:"timestamp" validate:"required"`
	Provider  string           `json:"provider" validate:"required"`
	Details   *json.RawMessage `json:"details" validate:"required"`
}

type PaymentError struct {
	Message        string           `json:"message"`
	Code           string           `json:"code"`
	PaymentDetails *json.RawMessage `json:"payment_details,omitempty"`
}

func (e *PaymentError) Error() string {
	return e.Message
}

type Result struct {
	Type           string           `json:"type"`
	ID             string           `json:"id,omitempty"`
	Success        bool             `json:"success"`
	Timestamp      time.Time        `json:"timestamp"`
	Error          *PaymentError    `json:"error,omitempty"`
	PaymentDetails *json.RawMessage `json:"payment_details,omitempty"`
}

type Provider interface {
	Auth(*pgxpool.Pool, *PaymentEvent) error
	Payout(*PaymentEvent) (*Result, error)
}
