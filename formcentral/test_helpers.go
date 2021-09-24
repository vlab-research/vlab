package main

import (
	"context"
	"testing"

	"github.com/jackc/pgconn"
	"github.com/jackc/pgx/v4/pgxpool"
)

func mustExec(t testing.TB, conn *pgxpool.Pool, sql string, arguments ...interface{}) (commandTag pgconn.CommandTag) {
	var err error
	if commandTag, err = conn.Exec(context.Background(), sql, arguments...); err != nil {
		t.Fatalf("Exec unexpectedly failed with %v: %v", sql, err)
	}
	return
}
