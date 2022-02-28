package main

import (
	"github.com/caarlos0/env/v6"
)

type Config struct {
	DbName string `env:"DATABASE_NAME,required"`
	DbHost string `env:"DATABASE_HOST,required"`
	DbPort int    `env:"DATABASE_PORT,required"`
	DbUser string `env:"DATABASE_USER,required"`
	Port   int    `env:"API_PORT,required"`
}

func getConfig() *Config {
	cfg := Config{}
	err := env.Parse(&cfg)
	handle(err)
	return &cfg
}
