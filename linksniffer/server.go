package main

import (
	"fmt"
	"github.com/labstack/echo/v4"
	"log"
	"net/http"
	"net/url"
	"os"
)

func main() {
	botserverUrl := os.Getenv("BOTSERVER_URL")

	client := &http.Client{}
	eventer := &Eventer{client, botserverUrl}
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
	pageid := c.QueryParam("pageid")
	u := c.QueryParam("url")
	p := c.QueryParam("p")

	if id == "" {
		e := fmt.Errorf("Cannot forward to url, lacking tracking id")
		return echo.NewHTTPError(http.StatusBadRequest, e)
	}

	if p == "" {
		p = "https"
	}

	u = p + "://" + u

	u, err := url.PathUnescape(u)
	if err != nil {
		log.Printf("Error sending event: %v", err)
		e := fmt.Errorf("URL could not be unescaped: %v", u)
		return echo.NewHTTPError(http.StatusBadRequest, e)
	}

	err = s.Eventer.Send(id, pageid, u)
	if err != nil {
		log.Printf("Error sending event: %v", err)
		return err
	}

	return c.Redirect(http.StatusFound, u)
}
