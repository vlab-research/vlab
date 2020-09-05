package main

import (
	"fmt"
	"log"
	"strings"

	"github.com/go-playground/validator/v10"
	"github.com/jackc/pgconn"
)

var (
	ForeignKeyHandler = MakePGHandler("23503")
	CheckConstraintHandler = MakePGHandler("23514")
)

type Handler func (error) (bool, string)

func ValidationHandler(err error) (bool, string) {
	_, ok := err.(validator.ValidationErrors)
	return ok, fmt.Sprintf("Handling validation error: %v", err)
}

func MakePGHandler(code string) Handler {
	return func (err error) (bool, string) {
		e, ok := err.(*pgconn.PgError)
		ok = (ok && e.Code == code)
		return ok, fmt.Sprintf("Handling Foreign Key error: %v", err)
	}
}

func getHandlers(cfg *Config) []Handler {
	lookup := map[string]Handler{
		"validation": ValidationHandler,
		"foreignkey": ForeignKeyHandler,
		"checkconstraint": CheckConstraintHandler,
	}


	handlers := []Handler{}
	if cfg.Handlers == "" {
		return handlers
	}

	names := strings.Split(cfg.Handlers, ",")
	for _, n := range names {
		n = strings.TrimSpace(n)
		handler, ok := lookup[n]
		if !ok {
			log.Fatalf("Scribble could not find handler named: %v", n)
		}
		handlers = append(handlers, handler)
	}
	return handlers
}

func tryHandlers(err error, handlers []Handler) error {
	for _, h := range handlers {
		if handled, msg := h(err); handled {
			log.Print(msg)
			return nil
		}
	}
	return err
}

func HandleErrors(errs <-chan error, handlers []Handler) <-chan error {
	fatalErrors := make(chan error)
	go func() {
		defer close(fatalErrors)
		for err := range errs {
			if tryHandlers(err, handlers) != nil {
				fatalErrors <- err
			}
		}
	}()
	return fatalErrors
}
