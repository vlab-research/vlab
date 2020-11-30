package main

import (
	"fmt"
	"log"
	"net/http"

	"github.com/caarlos0/env/v6"
	"github.com/jackc/pgx/v4/pgxpool"
	"github.com/labstack/echo/v4"
	"github.com/vlab-research/trans"
)

type Server struct {
	pool *pgxpool.Pool
}

func (s *Server) Health(c echo.Context) error {
	return c.String(http.StatusOK, "pong")
}

func (s *Server) GetTranslator(c echo.Context) error {
	surveyid := c.Param("surveyid")

	src, dest, err := getTranslationForms(s.pool, surveyid)
	if err != nil {
		msg := fmt.Sprintf("Could not get translation form for survey: %v. Error: %v", surveyid, err.Error())
		return echo.NewHTTPError(http.StatusNotFound, msg)
	}

	translator, err := trans.MakeTranslatorByShape(src, dest)

	if err != nil {
		msg := err.Error()
		return echo.NewHTTPError(http.StatusInternalServerError, fmt.Sprintf("Could not create translation mapping. Failed with the following error: %v", msg))
	}

	return c.JSON(http.StatusOK, translator)
}

type TranslatorRequest struct {
	Form        *trans.FormJson `json:"form"`
	Destination string          `json:"destination"`
	Self        bool            `json:"self"`
}

func (s *Server) CreateTranslator(c echo.Context) error {
	req := new(TranslatorRequest)
	var dest *trans.FormJson

	if err := c.Bind(req); err != nil {
		return err
	}

	if req.Self {
		dest = req.Form
	} else {
		var err error
		dest, err = getForm(s.pool, req.Destination)
		if err != nil {
			msg := fmt.Sprintf("Could not find destination form: %v", req.Destination)
			return echo.NewHTTPError(http.StatusNotFound, msg)
		}
	}

	translator, err := trans.MakeTranslatorByShape(req.Form, dest)
	if err != nil {
		msg := fmt.Sprintf("Could not create translation mapping. Failed with the following error: %v", err.Error())
		return echo.NewHTTPError(http.StatusBadRequest, msg)
	}

	return c.JSON(http.StatusOK, translator)
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
	cfg := getConfig()
	pool := getPool(&cfg)

	server := &Server{pool}

	e := echo.New()
	e.GET("/health", server.Health)
	e.GET("/translators/:surveyid", server.GetTranslator)
	e.POST("/translators", server.CreateTranslator)

	e.Logger.Fatal(e.Start(":1323"))
}
