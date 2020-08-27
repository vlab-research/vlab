package main

import (
    "context"
    "fmt"
    "log"
    "github.com/jackc/pgx/v4"
	"github.com/caarlos0/env/v6"
	"encoding/json"
	"net/http"
	"bytes"
)


func handle(err error) {
	if err != nil {
		log.Fatal(err)
	}
}

type Config struct {
	Db string `env:"CHATBASE_DATABASE,required"`
	User string `env:"CHATBASE_USER,required"`
	Password string `env:"CHATBASE_PASSWORD,required"`
	Host string `env:"CHATBASE_HOST,required"`
	Port string `env:"CHATBASE_PORT,required"`
	Botserver string `env:"BOTSERVER_URL,required"`
}

type Event struct {
	Type string `json:"type"` // redo
}

type ExternalEvent struct {
	User string `json:"user"`
	Page string `json:"page"`
	Event *Event `json:"event"`
}

func get(conn *pgx.Conn, ch chan *ExternalEvent) {
	query := `SELECT userid, pageid
              FROM states
              WHERE current_state = 'RESPONDING'
              AND updated > now() - interval '23 hour'
              AND now() - updated > interval '1 hour'`

    rows, err := conn.Query(context.Background(), query)
	handle(err)

	go func () {
		defer rows.Close()
		defer close(ch)

		for rows.Next() {
			var userid, pageid string
			err := rows.Scan(&userid, &pageid)
			handle(err)
			ch <- &ExternalEvent{userid, pageid, &Event{"redo"}}
		}
	}()
}

func send(cfg *Config, client *http.Client, e *ExternalEvent) error {

	body, err := json.Marshal(e)
	if err != nil {
		return err
	}

	resp, err := client.Post(cfg.Botserver, "application/json", bytes.NewBuffer(body))
	if err != nil {
		return err
	}

	code := resp.StatusCode
	if code != 200 {
		err := fmt.Errorf("Non 200 response from Botserver: %v", code)
		log.Print(err)
		return err
	}

	return nil
}


func process(cfg *Config, ch chan *ExternalEvent) {
	client := &http.Client{}

	counter := 0
	for e := range ch {
		err := send(cfg, client, e)
		handle(err)
		counter += 1
	}
	log.Printf("Successfully sent %v new redo events", counter)
}

func getConn(cfg *Config) (*pgx.Conn, context.Context) {
	conString := fmt.Sprintf("postgresql://%s@%s:%s/%s?sslmode=disable", cfg.User, cfg.Host, cfg.Port, cfg.Db)
    config, err := pgx.ParseConfig(conString)
	handle(err)

	ctx := context.Background()
    conn, err := pgx.ConnectConfig(ctx, config)
	handle(err)

	return conn, ctx
}

func main() {
	cfg := Config{}
	err := env.Parse(&cfg)
	handle(err)

	conn, ctx := getConn(&cfg)
	defer conn.Close(ctx)

	ch := make(chan *ExternalEvent)
	go get(conn, ch)
	process(&cfg, ch)
}
