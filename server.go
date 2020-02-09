package main

import (
	"net/http"
	"os"
	"log"
	"fmt"
	"net/url"
	"github.com/labstack/echo/v4"
)

func main() {
	botserverUrl := os.Getenv("BOTSERVER_URL")
	page := os.Getenv("FB_PAGE_ID")

	client := &http.Client{}
	eventer := &Eventer{client, botserverUrl, page}
	server := &Server{eventer}

	e := echo.New()
	e.GET("/", server.forward)
	e.GET("/health", server.health)

	e.Logger.Fatal(e.Start(":1323"))
}

type Server struct {
	Eventer *Eventer
}

func (s *Server) health(c echo.Context) error {
	return c.String(http.StatusOK, "pong")
}

func (s *Server) forward(c echo.Context) error {
	id := c.QueryParam("id")
	u := c.QueryParam("url")

	u, err := url.PathUnescape(u)
	if err != nil {
		log.Printf("Error sending event: %v", err)
		e := fmt.Errorf("URL could not be unescaped: %v", u)
		return echo.NewHTTPError(http.StatusBadRequest, e)
	}

	err = s.Eventer.Send(id, u)
	if err != nil {
		log.Printf("Error sending event: %v", err)
		return err
	}

	return c.Redirect(http.StatusFound, u)
}
