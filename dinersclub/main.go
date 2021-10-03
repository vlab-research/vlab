package main

import (
	"encoding/json"
	"fmt"
	"log"
	"time"

	"github.com/cenkalti/backoff"
	"github.com/confluentinc/confluent-kafka-go/kafka"
	"github.com/go-playground/validator/v10"
	"github.com/nandanrao/chance"
	"github.com/vlab-research/botparty"
	"github.com/vlab-research/spine"
	"github.com/jackc/pgx/v4/pgxpool"
	"github.com/dgraph-io/ristretto"
)

type DC struct {
	cfg       *Config
	pool      *pgxpool.Pool
	botparty  *botparty.BotParty
	cache     *ristretto.Cache
}

func handle(err error) {
	if err != nil {
		log.Fatal(err)
	}
}

func (dc *DC) Process(messages []*kafka.Message) error {
	tasks := []interface{}{}
	for _, m := range messages {
		pe := new(PaymentEvent)
		err := json.Unmarshal(m.Value, pe)
		if err != nil {
			return err
		}
		tasks = append(tasks, pe)
	}

	// this processes them all at once
	// maybe better for providers to have
	// a fixed pool size, limit concurrent
	// requests
	outch := chance.Pool(dc.cfg.PoolSize, chance.Flatten(tasks), dc.Work)
	for x := range outch {
		switch x.(type) {
		case error:
			return x.(error)
		default:
		}
	}

	return nil
}

func backoffTime(d time.Duration) *backoff.ExponentialBackOff {
	ebo := backoff.NewExponentialBackOff()
	ebo.MaxElapsedTime = d
	return ebo
}

func (dc *DC) sendResult(pe *PaymentEvent, res *Result) error {
	b, err := json.Marshal(res)
	jm := json.RawMessage(b)
	if err != nil {
		return err
	}

	op := func() error {
		ee := botparty.NewExternalEvent(pe.Userid, pe.Pageid, "external", &jm)
		return dc.botparty.Send(ee)
	}

	return backoff.Retry(op, backoffTime(dc.cfg.RetryBotserver))
}

func invalidProviderResult(pe *PaymentEvent) *Result {
	message := fmt.Sprintf("You requested payment by provider: %v but no provider with that name is configured", pe.Provider)
	err := &PaymentError{message, "INVALID_PROVIDER", nil}
	t := fmt.Sprintf("payment:%v", pe.Provider)
	res := &Result{Type: t, Success: false, Timestamp: time.Now().UTC(), Error: err}
	return res
}

func (dc *DC) checkCache(provider Provider, pe *PaymentEvent, user *User) (Provider, error) {
	key := pe.Provider + user.Id
	p, ok := dc.cache.Get(key)
	if ok {
		return p.(Provider), nil
	} 

	dc.cache.SetWithTTL(key, provider, 1, dc.cfg.CacheTTLTimeout)
	e := provider.Auth(user)
	if e != nil {
		return nil, e
	}

	return provider, nil
}

func (dc *DC) Job(pe *PaymentEvent) error {
	validate := validator.New()
	err := validate.Struct(pe)
	if err != nil {
		return err
	}

	provider, err := dc.getProvider(pe)
	if err != nil {
		return err
	}

	if provider == nil || !contains(dc.cfg.Providers, pe.Provider) {
		return dc.sendResult(pe, invalidProviderResult(pe))
	}

	user, err := provider.GetUserFromPaymentEvent(pe)
	if user == nil {
		return fmt.Errorf(`User not found for page id: %s`, pe.Pageid)
	}
	if err != nil {
		return err
	}

	res := new(Result)
	op := func() error {
		provider, e := dc.checkCache(provider, pe, user)
		if e != nil {
			return e
		}

		r, e := provider.Payout(pe)
		if e != nil {
			return e
		}
		res = r
		return nil
	}

	err = backoff.Retry(op, backoffTime(dc.cfg.RetryProvider))
	if err != nil {
		return err
	}

	return dc.sendResult(pe, res)
}

func (dc *DC) Work(i interface{}) interface{} {
	pe := i.(*PaymentEvent)
	return dc.Job(pe)
}

func contains(s []string, target string) bool {
	for _, x := range s {
		if x == target {
			return true
		}
	}
	return false
}

func (dc *DC) getProvider(event *PaymentEvent) (Provider, error) {
	switch event.Provider {
	case "fake":
		return NewFakeProvider()
	case "reloadly":
		return NewReloadlyProvider(dc.pool)
	}
	return nil, nil
}

func monitor(errs <-chan error) {
	e := <-errs
	log.Fatalf("DinersClub failed with error: %v", e)
}

func main() {
	cfg := getConfig()
	pool := getPool(cfg)
	bp := botparty.NewBotParty(cfg.Botserver)
	cache, err := ristretto.NewCache(&ristretto.Config{
		NumCounters: cfg.CacheNumCounters,
		MaxCost:     cfg.CacheMaxCost,
		BufferItems: cfg.CacheBufferItems,
	})
	handle(err)
	dc := &DC{cfg, pool, bp, cache}

	// TODO: need to change maximum poll interval for long retries!!

	c := spine.NewKafkaConsumer(cfg.KafkaTopic, cfg.KafkaBrokers, cfg.KafkaGroup,
		cfg.KafkaPollTimeout, cfg.KafkaBatchSize, cfg.KafkaBatchSize)

	errs := make(chan error)
	go monitor(errs)

	for {
		c.SideEffect(dc.Process, errs)
	}
}
