package main

import (
	"encoding/json"
	"fmt"
	"log"
	"time"

	"github.com/caarlos0/env/v6"
	"github.com/cenkalti/backoff"
	"github.com/confluentinc/confluent-kafka-go/kafka"
	"github.com/nandanrao/chance"
	"github.com/vlab-research/botparty"
	"github.com/vlab-research/spine"
)


type Config struct {
	Botserver string `env:"BOTSERVER_URL,required"`
	Provider string `env:"DINERSCLUB_PROVIDER,required"`
	KafkaBrokers string `env:"KAFKA_BROKERS,required"`
	KafkaPollTimeout time.Duration `env:"KAFKA_POLL_TIMEOUT,required"`
	Topic string `env:"KAFKA_TOPIC,required"`
	Group string `env:"KAFKA_GROUP,required"`
	BatchSize int `env:"SCRIBBLE_BATCH_SIZE,required"`
	ChunkSize int `env:"SCRIBBLE_CHUNK_SIZE,required"`
}

type DC struct {
	providerType string
	provider Provider
	botparty *botparty.BotParty
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
		err := x.(error)
		if err != nil {
			return err
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
	res := new(Result)
	op := func() error {
		r, e := dc.provider.Payout(pe)
		if e != nil {
			return e
		}
		res = r
		return nil
	}

	err := backoff.Retry(op, backoffTime(15*time.Minute))
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

	return backoff.Retry(op, backoffTime(60*time.Minute))
}

func (dc *DC) Work(i interface{}) interface{} {
	pe := i.(*PaymentEvent)
	return dc.Job(pe)
}


func getProvider(cfg *Config) (Provider, error) {
	lookup := map[string]func()(Provider, error){
		"fake": NewFakeProvider,
		"reloadly": NewReloadlyProvider,
	}

	providerFn, ok := lookup[cfg.Provider]
	if !ok {
		log.Fatalf("Cannot find provider with name: %v", cfg.Provider)
	}

	return providerFn()

}

func monitor(errs <-chan error) {
	e := <- errs
	log.Fatalf("DinersClub failed with error: %v", e)
}

func main() {
	cfg := Config{}
	err := env.Parse(&cfg)
	handle(err)

	provider, err := getProvider(&cfg)
	handle(err)

	bp := botparty.NewBotParty(cfg.Botserver)
	dc := &DC{cfg.Provider, provider, bp}

	c := spine.NewKafkaConsumer(cfg.Topic, cfg.KafkaBrokers, cfg.Group,
		cfg.KafkaPollTimeout, cfg.BatchSize, cfg.ChunkSize)

	errs := make(chan error)
	go monitor(errs)

	for {
		c.SideEffect(dc.Process, errs)
	}
}
