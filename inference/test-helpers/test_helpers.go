package connector

import (
	"context"
	"encoding/json"
	"fmt"
	"github.com/dghubble/sling"
	"github.com/jackc/pgconn"
	"github.com/jackc/pgx/v4"
	"github.com/jackc/pgx/v4/pgxpool"
	"github.com/tidwall/gjson"
	. "github.com/vlab-research/vlab/inference/inference-data"
	"io/ioutil"
	"log"
	"net/http"
	"net/http/httptest"
	"testing"
)

const (
	insertUser  = `insert into users(id) values($1) returning id`
	selectUser  = `select id from users where email = $1`
	insertStudy = `insert into studies(user_id, name, slug) values($1, $2, $3) returning id`
	insertConf  = `insert into study_confs(study_id, conf_type, conf) values($1, $2, $3)`
)

// NOTE: should we move these channel helpers elsewhere???

func Sliceit[T any](c <-chan T) []T {
	s := []T{}
	for x := range c {
		s = append(s, x)
	}
	return s
}

func GetString(d json.RawMessage, path string) string {
	s := gjson.GetBytes(d, path).Raw
	return s
}

func GetBodyAs(r *http.Request, t interface{}) (interface{}, error) {
	b, err := ioutil.ReadAll(r.Body)
	if err != nil {
		return nil, err
	}

	err = json.Unmarshal(b, t)
	if err != nil {
		return nil, err
	}

	return t, nil 
}

func MakeUserMap(e []*InferenceDataEvent) map[string]map[string]*InferenceDataEvent {

	lookup := map[string]map[string]*InferenceDataEvent{}

	for _, event := range e {
		_, ok := lookup[event.User.ID]
		if ok {
			lookup[event.User.ID][event.Variable] = event

		} else {
			lookup[event.User.ID] = map[string]*InferenceDataEvent{
				event.Variable: event,
			}
		}
	}

	return lookup
}

// NOTE: should we move the http helpers elsewhere???

type TestTransport func(req *http.Request) (*http.Response, error)

func (r TestTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	return r(req)
}

func TestServer(handler func(http.ResponseWriter, *http.Request)) (*httptest.Server, *sling.Sling) {
	ts := httptest.NewServer(http.HandlerFunc(handler))
	sli := sling.New().Client(&http.Client{}).Base(ts.URL)
	return ts, sli
}

func TestServerMux() (*httptest.Server, *http.ServeMux) {
	mux := http.NewServeMux()
	ts := httptest.NewServer(mux)
	return ts, mux
}

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
