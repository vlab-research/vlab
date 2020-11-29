package main

import (
	"context"
	"fmt"
	"github.com/jackc/pgx/v4/pgxpool"
)

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
