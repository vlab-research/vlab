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
	client := &http.Client{}
	eventer := &Eventer{client, botserverUrl}
	server := &Server{eventer}

	e := echo.New()
	e.GET("/", server.forward)

	e.Logger.Fatal(e.Start(":1323"))
}

type Server struct {
	Eventer *Eventer
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
