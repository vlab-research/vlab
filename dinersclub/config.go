package main

import (
	"time"

	"github.com/caarlos0/env/v6"
)

type Config struct {
	Botserver        string        `env:"BOTSERVER_URL,required"`
	KafkaBrokers     string        `env:"KAFKA_BROKERS,required"`
	KafkaPollTimeout time.Duration `env:"KAFKA_POLL_TIMEOUT,required"`
	PoolSize         int           `env:"DINERSCLUB_POOL_SIZE,required"`
	KafkaTopic       string        `env:"KAFKA_TOPIC,required"`
	KafkaGroup       string        `env:"KAFKA_GROUP,required"`
	KafkaBatchSize   int           `env:"DINERSCLUB_BATCH_SIZE,required"`
	RetryBotserver   time.Duration `env:"DINERSCLUB_RETRY_BOTSERVER,required"`
	RetryProvider    time.Duration `env:"DINERSCLUB_RETRY_PROVIDER,required"`
	Providers        []string      `env:"DINERSCLUB_PROVIDERS" envSeparator:","`
}

func getConfig() *Config {
	cfg := Config{}
	err := env.Parse(&cfg)
	handle(err)
	return &cfg
}
