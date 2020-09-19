package main

import (
	"encoding/json"
	"net/http"

	"time"

	"github.com/caarlos0/env/v6"
	"github.com/nandanrao/go-reloadly/reloadly"
)


type ReloadlyConfig struct {
	Sandbox bool `env:"RELOADLY_SANDBOX,required"`
	ID string `env:"RELOADLY_ID,required"`
	Secret string `env:"RELOADLY_SECRET,required"`
}

type ReloadlyProvider struct {
	config *ReloadlyConfig
	svc *reloadly.Service
}

func NewReloadlyProvider() (Provider, error){
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

func errorResult(res *Result, err error) (*Result, error) {
	res.Success = false
	if e, ok := err.(reloadly.APIError); ok {
		res.Error = &PaymentError{ e.Message, e.ErrorCode }
		return res, nil
	}
	if e, ok := err.(reloadly.ReloadlyError); ok {
		res.Error = &PaymentError{ e.Message, e.ErrorCode }
		return res, nil
	}

	// any other type of error should be considered a
	// system error and should be retried/logged.
	return res, err
}

func (p *ReloadlyProvider) Payout(event *PaymentEvent) (*Result, error) {
	job := new(reloadly.TopupJob)
	err := json.Unmarshal(event.Details, job)
	if err != nil {
		return nil, err
	}

	result := &Result{}
	result.ID = job.ID
	result.Type = "payment:reloadly"

	worker := reloadly.TopupWorker(*p.svc)
	r, err := worker.DoJob(job)

	if err != nil {
		return errorResult(result, err)
	}

	result.Success = true
	result.Timestamp = time.Time(*r.TransactionDate)
	return result, nil
}
