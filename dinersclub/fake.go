package main

import (
	"encoding/json"
	"time"
)

type FakeProvider struct {
	getUserFromPaymentEvent GetUserFromPaymentEvent
	auth Auth
}

type FakeDetails struct {
	Result *Result `json:"result"`
}

func NewFakeProvider(gu GetUserFromPaymentEvent, auth Auth) (Provider, error) {
	return &FakeProvider{getUserFromPaymentEvent: gu, auth: auth}, nil
}

func (p *FakeProvider) GetUserFromPaymentEvent(event *PaymentEvent) (*User, error) {
	return p.getUserFromPaymentEvent(event)
}

func getUserFromFakePaymentEvent(event *PaymentEvent) (*User, error) {
	return &User{Id:"test-id"}, nil
}

func (p *FakeProvider) Auth(user *User) error {
	return p.auth(user)
}

func auth(user *User) error {
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
