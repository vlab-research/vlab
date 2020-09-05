package main

import (
	"testing"
	"errors"

	"github.com/stretchr/testify/assert"
)

func TestHandleErrorsCatchesEverything(t *testing.T) {

	handlers := []Handler{
		func (e error) (bool, string){
			return true, ""
		},
	}

	done := make(chan bool)
	errs := make(chan error)

	e := HandleErrors(errs, handlers)

	go func() {
		errs <- errors.New("hi")
		close(errs)
	}()

	go func() {
		defer close(done)
		for _ = range e {
			t.Error("shouldnt have had anything in this channel")
		}
	}()

	<- done
}

func TestHandleErrorsWorksWithNoHandlers(t *testing.T) {
	handlers := []Handler{}

	done := make(chan bool)
	errs := make(chan error)
	e := HandleErrors(errs, handlers)

	go func() {
		errs <- &TestError{"bar"}
		errs <- errors.New("foo")
		close(errs)
	}()

	go func() {
		count := 0
		defer close(done)
		for err := range e {
			count += 1
			assert.NotNil(t, err)
		}
		assert.Equal(t, 2, count)
	}()

	<- done
}


func TestHandleErrorsPassesSomeErrors(t *testing.T) {
	handlers := []Handler{
		func (e error) (bool, string){
			if _, ok := e.(*TestError); ok {
				return true, ""
			}
			return false, ""
		},
	}

	done := make(chan bool)
	errs := make(chan error)
	e := HandleErrors(errs, handlers)

	go func() {
		errs <- &TestError{"bar"}
		errs <- errors.New("foo")
		close(errs)
	}()

	go func() {
		count := 0
		defer close(done)
		for err := range e {
			count += 1
			_, ok := err.(*TestError)
			assert.Equal(t, ok, false)
		}
		assert.Equal(t, count, 1)
	}()

	<- done
}


func TestGetHandlers(t *testing.T) {
	res := getHandlers(&Config{Handlers: ""})
	assert.Equal(t, 0, len(res))

	res = getHandlers(&Config{Handlers: "foreignkey"})
	assert.Equal(t, 1, len(res))

	res = getHandlers(&Config{Handlers: "foreignkey,validation"})
	assert.Equal(t, 2, len(res))

	res = getHandlers(&Config{Handlers: "foreignkey, validation"})
	assert.Equal(t, 2, len(res))

	res = getHandlers(&Config{Handlers: " foreignkey "})
	assert.Equal(t, 1, len(res))
}
