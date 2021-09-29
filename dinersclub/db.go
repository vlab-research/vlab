package main

import (
	"context"
	"fmt"
	"encoding/json"

	"github.com/jackc/pgx/v4/pgxpool"
)

type Credentials struct {
	Details *json.RawMessage
}

func getPool(cfg *Config) *pgxpool.Pool {
	con := fmt.Sprintf("postgresql://%s@%s:%d/%s?sslmode=disable", cfg.DbUser, cfg.DbHost, cfg.DbPort, cfg.DbName)
	config, err := pgxpool.ParseConfig(con)
	handle(err)

	config.MaxConns = int32(cfg.DbMaxConns)

	ctx := context.Background()
	pool, err := pgxpool.ConnectConfig(ctx, config)
	handle(err)

	return pool
}
