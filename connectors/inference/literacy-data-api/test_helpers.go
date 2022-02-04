package main

import (
	"context"
	"fmt"
	"testing"

	"github.com/jackc/pgconn"
	"github.com/jackc/pgx/v4"
	"github.com/jackc/pgx/v4/pgxpool"
)

func exec(conn *pgxpool.Pool, sql string, arguments ...interface{}) (*pgconn.CommandTag, error) {
	commandTag, err := conn.Exec(context.Background(), sql, arguments...)

	if err != nil {
		return nil, fmt.Errorf("Exec unexpectedly failed with %v: %v", sql, err)
	}

	return &commandTag, nil
}

func mustExec(t *testing.T, conn *pgxpool.Pool, sql string, arguments ...interface{}) {
	_, err := exec(conn, sql, arguments...)
	if err != nil {
		t.Fatal(err.Error())
	}
}

func rowStrings(rows pgx.Rows) []*string {
	res := []*string{}
	for rows.Next() {
		col := new(string)
		_ = rows.Scan(&col)
		res = append(res, col)
	}
	return res
}

func getCol(pool *pgxpool.Pool, table string, col string) []*string {
	rows, err := pool.Query(context.Background(), fmt.Sprintf("select %v from %v", col, table))
	if err != nil {
		panic(err)
	}

	return rowStrings(rows)
}

func testPool() *pgxpool.Pool {
	config, err := pgxpool.ParseConfig("postgres://root@localhost:5433/test")
	handle(err)

	ctx := context.Background()
	pool, err := pgxpool.ConnectConfig(ctx, config)
	handle(err)

	exec(pool, "CREATE DATABASE IF NOT EXISTS test")

	return pool
}
