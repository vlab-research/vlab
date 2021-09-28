package main

import (
	"context"
	"fmt"
	"encoding/json"

	"github.com/jackc/pgx/v4"
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

func getCredentials(pool *pgxpool.Pool, userid string, entity string) (*Credentials, error) {
	query := `SELECT details FROM credentials WHERE userid=$1 AND entity=$2 LIMIT 1`
	var c Credentials
	row := pool.QueryRow(context.Background(), query, userid, entity)
	err := row.Scan(&c.Details)

	if err == pgx.ErrNoRows {
		return nil, nil
	}

	return &c, err
}
