package main

import (
	"encoding/json"
	"time"
	"fmt"
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
	} else if event.Pageid == "test-auth-page" {
		return &User{Id:"test-auth-user"}, nil
	}
	return nil, nil
}

func (p *FakeProvider) Auth(user *User) error {
	if user.Id == "test-auth-user" {
		return fmt.Errorf(`No credentials were found for user: %s`, user.Id)
	}
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
