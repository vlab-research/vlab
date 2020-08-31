package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/caarlos0/env/v6"
	"github.com/jackc/pgx/v4/pgxpool"
)

type Config struct {
	Db string `env:"CHATBASE_DATABASE,required"`
	User string `env:"CHATBASE_USER,required"`
	Password string `env:"CHATBASE_PASSWORD,required"`
	Host string `env:"CHATBASE_HOST,required"`
	Port string `env:"CHATBASE_PORT,required"`
	KafkaBrokers string `env:"KAFKA_BROKERS,required"`
	KafkaPollTimeout time.Duration `env:"KAFKA_POLL_TIMEOUT,required"`
	Topic string `env:"KAFKA_TOPIC,required"`
	Group string `env:"KAFKA_GROUP,required"`
	BatchSize int `env:"SCRIBBLE_CHUNK_SIZE,required"`
	ChunkSize int `env:"SCRIBBLE_BATCH_SIZE,required"`
	Destination string `env:"SCRIBBLE_DESTINATION,required"`
}

func monitor(errs <-chan error) {
	e := <- errs
	log.Fatalf("Scribble failed with error: %v", e)
}

func handle(err error) {
	if err != nil {
		log.Fatal(err)
	}
}

func getPool(cfg *Config) *pgxpool.Pool {
	conString := fmt.Sprintf("postgresql://%s@%s:%s/%s?sslmode=disable", cfg.User, cfg.Host, cfg.Port, cfg.Db)
    config, err := pgxpool.ParseConfig(conString)
	handle(err)

	config.MaxConns = int32(32)

	ctx := context.Background()
    pool, err := pgxpool.ConnectConfig(ctx, config)
	handle(err)

	return pool
}

func getMarshaller(cfg *Config) MarshalWriteable {
	name := cfg.Destination
	marshallers := map[string]MarshalWriteable{
		"states": StateMarshaller,
		"responses": ResponseMarshaller,
		"messages": MessageMarshaller,
	}

	m, ok := marshallers[name]
	if !ok {
		log.Fatalf("Scribble couldnt find a marshaller for destination %v", name)
	}
	return m
}

func main() {
	cfg := Config{}
	err := env.Parse(&cfg)
	handle(err)

	pool := getPool(&cfg)

	c := NewKafkaConsumer(cfg.Topic, cfg.KafkaBrokers, cfg.Group,
		cfg.KafkaPollTimeout, cfg.BatchSize, cfg.ChunkSize)

	errs := make(chan error)
	monitor(errs)

	writer := GetWriter(pool, getMarshaller(&cfg))

	for {
		c.SideEffect(writer.Write, errs)
	}
}
