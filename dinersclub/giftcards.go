package main

import (
	"encoding/json"
	"time"

	"github.com/go-playground/validator/v10"
	"github.com/jackc/pgx/v4/pgxpool"
	"github.com/vlab-research/go-reloadly/reloadly"
)

type GiftCardsProvider struct {
	ReloadlyProvider
}

func NewGiftCardsProvider(pool *pgxpool.Pool) (Provider, error) {
	cfg := getConfig()
	svc := reloadly.NewGiftCards()
	if cfg.Sandbox {
		svc.Sandbox()
	}
	p := ReloadlyProvider{pool, svc, "INVALID_GIFT_CARD_DETAILS"}
	return &GiftCardsProvider{p}, nil
}

func (p *GiftCardsProvider) Payout(event *PaymentEvent) (*Result, error) {
	order := new(reloadly.GiftCardOrder)
	err := json.Unmarshal(*event.Details, &order)
	if err != nil {
		return nil, err
	}

	result := &Result{}
	result.Type = "payment:giftcard"
	result.ID = order.ID

	validate := validator.New()
	err = validate.Struct(order)
	if err != nil {
		return p.formatError(result, err, event.Details)
	}

	t, err := p.svc.GiftCards().Order(*order)
	if err != nil {
		return p.formatError(result, err, event.Details)
	}

	result.Success = true
	result.Timestamp = time.Time(*t.TransactionCreatedTime)
	result.PaymentDetails = event.Details
	return result, nil
}
