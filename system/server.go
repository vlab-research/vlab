package main

import (
	"fmt"
	"github.com/jackc/pgx/v4/pgxpool"
	"github.com/labstack/echo/v4"
	"log"
	"net/http"
)

type Server struct {
	pool       *pgxpool.Pool
	tableNames []string
}

type ResetParams struct {
	Tables []string `query:"table"`
}

func (s *Server) ResetDb(c echo.Context) error {

	params := new(ResetParams)
	if err := c.Bind(params); err != nil {
		return err
	}

	// If no tables supplied, clear all of them
	if len(params.Tables) == 0 {
		params.Tables = s.tableNames
	}

	err := resetDb(s.pool, params.Tables)
	if err != nil {
		return err
	}
	return c.String(http.StatusOK, "ok")
}

func handle(err error) {
	if err != nil {
		log.Fatal(err)
	}
}

func main() {
	cfg := getConfig()
	pool := getPool(cfg)
	tableNames, err := getTableNames(pool)
	handle(err)
	server := &Server{pool, tableNames}

	e := echo.New()
	e.GET("/resetdb", server.ResetDb)

	address := fmt.Sprintf(`:%d`, cfg.Port)
	e.Logger.Fatal(e.Start(address))
}
