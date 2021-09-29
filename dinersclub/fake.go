package main

import (
	"encoding/json"
	"time"
	"errors"

	"github.com/jackc/pgx/v4/pgxpool"
)

type FakeProvider struct{}

type FakeDetails struct {
	Result *Result `json:"result"`
}

func NewFakeProvider() (Provider, error) {
	return &FakeProvider{}, nil
}

func (p *FakeProvider) Auth(pool *pgxpool.Pool, userid string) error {
	crds, err := getCredentials(pool, userid, "fake")
	if crds == nil {
		return errors.New("No credentials were found to authorize the user")
	}
}

func (p *FakeProvider) Payout(event *PaymentEvent) (*Result, error) {
	var details FakeDetails
	err := json.Unmarshal(*event.Details, &details)

	if err != nil {
		return nil, err
	}

	time.Sleep(10 * time.Millisecond)
	return details.Result, nil
}
