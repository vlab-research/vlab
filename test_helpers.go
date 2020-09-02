package main

import (
	"context"
	"testing"
	"fmt"

	"github.com/jackc/pgconn"
	"github.com/jackc/pgx/v4/pgxpool"
)

func getCol(pool *pgxpool.Pool, table string, col string) []string {
	rows, err := pool.Query(context.Background(), fmt.Sprintf("select %v from %v", col, table))
	if err != nil {
		panic(err)
	}

	res := []string{}
	for rows.Next() {
		var col string
		_ = rows.Scan(&col)
		res = append(res, col)
	}
	return res
}

func mustExec(t testing.TB, conn *pgxpool.Pool, sql string, arguments ...interface{}) (commandTag pgconn.CommandTag) {
	var err error
	if commandTag, err = conn.Exec(context.Background(), sql, arguments...); err != nil {
		t.Fatalf("Exec unexpectedly failed with %v: %v", sql, err)
	}
	return
}


func testPool() *pgxpool.Pool {
    config, err := pgxpool.ParseConfig("postgres://root@localhost:5433/test")
	handle(err)

	ctx := context.Background()
    pool, err := pgxpool.ConnectConfig(ctx, config)
	handle(err)

	return pool
}
