package main

import (
	"encoding/json"
	"time"

	"github.com/caarlos0/env/v6"
	"github.com/go-playground/validator/v10"
	"github.com/nandanrao/go-reloadly/reloadly"
)

type ReloadlyConfig struct {
	Sandbox bool   `env:"RELOADLY_SANDBOX,required"`
	ID      string `env:"RELOADLY_ID,required"`
	Secret  string `env:"RELOADLY_SECRET,required"`
}

type ReloadlyProvider struct {
	config *ReloadlyConfig
	svc    *reloadly.Service
}

func NewReloadlyProvider() (Provider, error) {
	cfg := new(ReloadlyConfig)
	err := env.Parse(cfg)
	if err != nil {
		return nil, err
	}

	svc := reloadly.New()
	if cfg.Sandbox {
		svc.Sandbox()
	}

	err = svc.Auth(cfg.ID, cfg.Secret)
	if err != nil {
		return nil, err
	}

	rp := &ReloadlyProvider{cfg, svc}
	return rp, nil
}

func reloadlyErrorResult(res *Result, err error, details *json.RawMessage) (*Result, error) {
	res.Success = false

	// TODO: catch 500 errors and "try again later" errors
	// for retrying...
	// PHONE_RECENTLY_RECHARGED
	// TRANSACTION_CANNOT_BE_PROCESSED_AT_THE_MOMENT
	// PROVIDER_INTERNAL_ERROR
	// SERVICE_TO_OPERATOR_TEMPORARILY_UNAVAILABLE

	// what to do if fallback is not provider you checked
	// has correct option types?

	// IMPOSSIBLE_AMOUNT
	// Add special message in typeform logic to deal with this???
	if e, ok := err.(reloadly.APIError); ok {
		res.Error = &PaymentError{e.Message, e.ErrorCode, details}
		return res, nil
	}
	if e, ok := err.(reloadly.ReloadlyError); ok {
		res.Error = &PaymentError{e.Message, e.ErrorCode, details}
		return res, nil
	}
	if e, ok := err.(validator.ValidationErrors); ok {
		res.Error = &PaymentError{e.Error(), "INVALID_PAYMENT_DETAILS", details}
		return res, nil
	}

	// any other type of error should be considered a
	// system error and should be retried/logged.
	return res, err
}

func (p *ReloadlyProvider) Payout(event *PaymentEvent) (*Result, error) {
	job := new(reloadly.TopupJob)
	err := json.Unmarshal(*event.Details, job)
	if err != nil {
		return nil, err
	}

	result := &Result{}
	result.Type = "payment:reloadly"
	result.ID = job.ID

	validate := validator.New()
	err = validate.Struct(job)
	if err != nil {
		return reloadlyErrorResult(result, err, event.Details)
	}

	worker := reloadly.TopupWorker(*p.svc)
	r, err := worker.DoJob(job)

	if err != nil {
		return reloadlyErrorResult(result, err, event.Details)
	}

	result.Success = true
	result.Timestamp = time.Time(*r.TransactionDate)
	result.PaymentDetails = event.Details
	return result, nil
}
