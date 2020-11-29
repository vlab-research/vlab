package main

import (
	"log"
	"net/http"

	"github.com/caarlos0/env/v6"
	"github.com/labstack/echo/v4"
)

type Server struct {
}

func (s *Server) health(c echo.Context) error {
	return c.String(http.StatusOK, "pong")
}

func (s *Server) survey(c echo.Context) error {
	return c.String(http.StatusOK, "a survey")
}

func (s *Server) translate(c echo.Context) error {
	return c.String(http.StatusOK, "foo")
}

type Config struct {
	Db       string `env:"CHATBASE_DATABASE,required"`
	User     string `env:"CHATBASE_USER,required"`
	Password string `env:"CHATBASE_PASSWORD,required"`
	Host     string `env:"CHATBASE_HOST,required"`
	Port     string `env:"CHATBASE_PORT,required"`
}

func getConfig() Config {
	cfg := Config{}
	err := env.Parse(&cfg)
	handle(err)
	return cfg
}

func handle(err error) {
	if err != nil {
		log.Fatal(err)
	}
}

func main() {

	server := &Server{}

	e := echo.New()
	e.GET("/health", server.health)
	e.GET("/surveys", server.health)

	e.GET("/translate", server.translate)

	e.Logger.Fatal(e.Start(":1323"))
}
