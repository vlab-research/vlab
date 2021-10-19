package main

import (
	"github.com/caarlos0/env/v6"
)

type Config struct {
	DbName     string `env:"CHATBASE_DATABASE,required"`
	DbHost     string `env:"CHATBASE_HOST,required"`
	DbPort     int    `env:"CHATBASE_PORT,required"`
	DbUser     string `env:"CHATBASE_USER,required"`
	DbMaxConns int    `env:"CHATBASE_MAX_CONNECTIONS,required"`
	Port       int    `env:"PORT,required"`
}

func getConfig() *Config {
	cfg := Config{}
	err := env.Parse(&cfg)
	handle(err)
	return &cfg
}
