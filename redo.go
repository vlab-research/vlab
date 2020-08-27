package main

import (
    "context"
    "fmt"
    "log"
	"strings"
    "github.com/jackc/pgx/v4/pgxpool"
	"github.com/caarlos0/env/v6"
	"sync"
	"encoding/json"
	"net/http"
	"bytes"
)

func merge(cs ...<-chan *ExternalEvent) <-chan *ExternalEvent {
    var wg sync.WaitGroup
    out := make(chan *ExternalEvent)

    // Start an output goroutine for each input channel in cs.  output
    // copies values from c to out until c is closed, then calls wg.Done.
    output := func(c <-chan *ExternalEvent) {
        for n := range c {
            out <- n
        }
        wg.Done()
    }
    wg.Add(len(cs))
    for _, c := range cs {
        go output(c)
    }

    // Start a goroutine to close out once all the output goroutines are
    // done.  This must start after the wg.Add call.
    go func() {
        wg.Wait()
        close(out)
    }()
    return out
}

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
	Codes string `env:"REDO_FB_CODES,required"`
}

func redoCodes(cfg *Config) []string {
	return strings.Split(cfg.Codes, ",")
}

type Event struct {
	Type string `json:"type"` // redo
}

type ExternalEvent struct {
	User string `json:"user"`
	Page string `json:"page"`
	Event *Event `json:"event"`
}

func get(conn *pgxpool.Pool, ch chan *ExternalEvent, query string, args ...interface{}) {
    rows, err := conn.Query(context.Background(), query, args...)
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

func respondings(conn *pgxpool.Pool) chan *ExternalEvent {
	ch := make(chan *ExternalEvent)
	query := `SELECT userid, pageid
              FROM states
              WHERE current_state = 'RESPONDING'
              AND updated > now() - interval '23 hour'
              AND now() - updated > interval '1 hour'`

	get(conn, ch, query)
	return ch
}

func blocked(cfg *Config, conn *pgxpool.Pool) chan *ExternalEvent {
	ch := make(chan *ExternalEvent)
	query := `SELECT userid, pageid 
              FROM states 
              WHERE state_json->'error'->>'code' = ANY($1)`

	get(conn, ch, query, redoCodes(cfg))
	return ch
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


func process(cfg *Config, ch <-chan *ExternalEvent) {
	client := &http.Client{}

	counter := 0
	for e := range ch {
		err := send(cfg, client, e)
		handle(err)
		counter += 1
	}
	log.Printf("Successfully sent %v new redo events", counter)
}

func getConn(cfg *Config) *pgxpool.Pool {
	conString := fmt.Sprintf("postgresql://%s@%s:%s/%s?sslmode=disable", cfg.User, cfg.Host, cfg.Port, cfg.Db)
    config, err := pgxpool.ParseConfig(conString)
	handle(err)

	ctx := context.Background()
    pool, err := pgxpool.ConnectConfig(ctx, config)
	handle(err)

	return pool
}

func main() {
	cfg := Config{}
	err := env.Parse(&cfg)
	handle(err)

	conn := getConn(&cfg)
	defer conn.Close()
	
	ch := merge(respondings(conn), blocked(&cfg, conn))
	process(&cfg, ch)
}
