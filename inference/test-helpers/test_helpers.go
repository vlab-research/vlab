package connector

import (
	"context"
	"fmt"
	"log"
	"testing"

	"github.com/jackc/pgconn"
	"github.com/jackc/pgx/v4"
	"github.com/jackc/pgx/v4/pgxpool"
)

const (
	insertUser  = `insert into users(id) values($1) returning id`
	selectUser  = `select id from users where email = $1`
	insertStudy = `insert into studies(user_id, name, slug) values($1, $2, $3) returning id`
	insertConf  = `insert into study_confs(study_id, conf_type, conf) values($1, $2, $3)`
)

func CreateUser(pool *pgxpool.Pool, id string) string {
	var res string
	err := pool.QueryRow(context.Background(), selectUser, id).Scan(&res)
	if err == nil {
		return res
	}

	err = pool.QueryRow(context.Background(), insertUser, id).Scan(&res)
	if err != nil {
		log.Fatal(err)
	}
	return res
}

func CreateStudy(pool *pgxpool.Pool, name string) string {
	user := CreateUser(pool, fmt.Sprintf("%s@email", name))

	var id string
	err := pool.QueryRow(context.Background(), insertStudy, user, name, name).Scan(&id)
	if err != nil {
		log.Fatal(err)
	}
	return id
}

func handle(err error) {
	if err != nil {
		log.Fatal(err)
	}
}

func Exec(conn *pgxpool.Pool, sql string, arguments ...interface{}) (*pgconn.CommandTag, error) {
	commandTag, err := conn.Exec(context.Background(), sql, arguments...)

	if err != nil {
		return nil, fmt.Errorf("Exec unexpectedly failed with %v: %v", sql, err)
	}

	return &commandTag, nil
}

func MustExec(t *testing.T, conn *pgxpool.Pool, sql string, arguments ...interface{}) {
	_, err := Exec(conn, sql, arguments...)
	if err != nil {
		t.Fatal(err.Error())
	}
}

func RowStrings(rows pgx.Rows) []*string {
	res := []*string{}
	for rows.Next() {
		col := new(string)
		_ = rows.Scan(&col)
		res = append(res, col)
	}
	return res
}

func GetCol(pool *pgxpool.Pool, table string, col string) []*string {
	rows, err := pool.Query(context.Background(), fmt.Sprintf("select %v from %v", col, table))
	if err != nil {
		panic(err)
	}

	return RowStrings(rows)
}

func TestPool() *pgxpool.Pool {
	config, err := pgxpool.ParseConfig("postgres://root@localhost:5433/test")
	handle(err)

	ctx := context.Background()
	pool, err := pgxpool.ConnectConfig(ctx, config)
	handle(err)

	Exec(pool, "CREATE DATABASE IF NOT EXISTS test")

	return pool
}
