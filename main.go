package main

import (
	"encoding/json"
	"fmt"
	"log"
	"time"

	"github.com/caarlos0/env/v6"
	"github.com/cenkalti/backoff"
	"github.com/confluentinc/confluent-kafka-go/kafka"
	"github.com/go-playground/validator/v10"
	"github.com/nandanrao/chance"
	"github.com/vlab-research/botparty"
	"github.com/vlab-research/spine"
)

type Config struct {
	Botserver        string        `env:"BOTSERVER_URL,required"`
	Provider         string        `env:"DINERSCLUB_PROVIDER,required"`
	KafkaBrokers     string        `env:"KAFKA_BROKERS,required"`
	KafkaPollTimeout time.Duration `env:"KAFKA_POLL_TIMEOUT,required"`
	Topic            string        `env:"KAFKA_TOPIC,required"`
	Group            string        `env:"KAFKA_GROUP,required"`
	BatchSize        int           `env:"DINERSCLUB_BATCH_SIZE,required"`
	ChunkSize        int           `env:"DINERSCLUB_CHUNK_SIZE,required"`
	RetryBotserver   time.Duration `env:"DINERSCLUB_RETRY_BOTSERVER,required"`
	RetryProvider    time.Duration `env:"DINERSCLUB_RETRY_PROVIDER,required"`
	Providers        []string      `env:"DINERSCLUB_PROVIDERS" envSeparator:","`
}

type DC struct {
	cfg       *Config
	providers map[string]Provider
	botparty  *botparty.BotParty
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

	outch := chance.Pool(len(tasks), chance.Flatten(tasks), dc.Work)
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

func (dc *DC) Job(pe *PaymentEvent) error {
	validate := validator.New()
	err := validate.Struct(pe)
	if err != nil {
		return err
	}

	provider, ok := dc.providers[pe.Provider]
	if !ok {
		return fmt.Errorf("Cannot find provider named: %v", pe.Provider)
	}

	res := new(Result)
	op := func() error {
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

	b, err := json.Marshal(res)
	jm := json.RawMessage(b)
	if err != nil {
		return err
	}

	op = func() error {
		ee := botparty.NewExternalEvent(pe.Userid, pe.Pageid, "external", &jm)
		return dc.botparty.Send(ee)
	}

	return backoff.Retry(op, backoffTime(dc.cfg.RetryBotserver))
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

func getProviders(cfg *Config) (map[string]Provider, error) {
	lookup := map[string]func() (Provider, error){
		"fake":     NewFakeProvider,
		"reloadly": NewReloadlyProvider,
	}

	providers := map[string]Provider{}
	for name, fn := range lookup {
		if contains(cfg.Providers, name) {
			p, err := fn()
			if err != nil {
				return nil, err
			}
			providers[name] = p
		}
	}

	return providers, nil
}

func monitor(errs <-chan error) {
	e := <-errs
	log.Fatalf("DinersClub failed with error: %v", e)
}

func main() {
	cfg := new(Config)
	err := env.Parse(cfg)
	handle(err)

	providers, err := getProviders(cfg)
	handle(err)

	bp := botparty.NewBotParty(cfg.Botserver)
	dc := &DC{cfg, providers, bp}

	c := spine.NewKafkaConsumer(cfg.Topic, cfg.KafkaBrokers, cfg.Group,
		cfg.KafkaPollTimeout, cfg.BatchSize, cfg.ChunkSize)

	errs := make(chan error)
	go monitor(errs)

	for {
		c.SideEffect(dc.Process, errs)
	}
}
