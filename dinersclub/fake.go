package main

import (
	"encoding/json"
	"time"
)

type FakeProvider struct{}

type FakeDetails struct {
	Result *Result `json:"result"`
}

func NewFakeProvider() (Provider, error) {
	return &FakeProvider{}, nil
}

func (p *FakeProvider) GetUserFromPaymentEvent(event *PaymentEvent) (*User, error) {
	if event.Pageid == "page" || event.Pageid == "935593143497601" {
		return &User{Id:"test-id"}, nil
	}
	return nil, nil
}

func (p *FakeProvider) Auth(user *User) error {
	return nil
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
