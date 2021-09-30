package main

import (
	"encoding/json"
	"time"
	"context"
	"errors"
	"fmt"

	"github.com/go-playground/validator/v10"
	"github.com/nandanrao/go-reloadly/reloadly"
	"github.com/jackc/pgx/v4"
	"github.com/jackc/pgx/v4/pgxpool"
)

type ReloadlyProvider struct {
	svc *reloadly.Service
}

func NewReloadlyProvider() (Provider, error) {
	cfg := getConfig() 
	svc := reloadly.New()
	if cfg.Sandbox {
		svc.Sandbox()
	}
	return &ReloadlyProvider{svc}, nil
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

func (p *ReloadlyProvider) getCredentials(pool *pgxpool.Pool, pageid string) (*Credentials, error) {
	query := `SELECT details FROM credentials WHERE facebook_page_id=$1 LIMIT 1`
	var c Credentials
	row := pool.QueryRow(context.Background(), query, pageid)
	err := row.Scan(&c.Details)

	if err == pgx.ErrNoRows {
		return nil, nil
	}

	return &c, err
}

func (p *ReloadlyProvider) Auth(pool *pgxpool.Pool, event *PaymentEvent) error {
	crds, err := p.getCredentials(pool, event.Pageid)
	if err != nil {
		return err
	}
	if crds == nil {
		msg := fmt.Sprintf(`No credentials were found for pageid: %s`, event.Pageid)
		return errors.New(msg)
	}

	auth := struct {
		id string
		secret string
	}{}
	err = json.Unmarshal(*crds.Details, &auth)
	if err != nil {
		return err
	}

	err = p.svc.Auth(auth.id, auth.secret)
	return err
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
