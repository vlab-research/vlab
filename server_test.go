package main

import (
	"net/http"
	"net/url"
	"net/http/httptest"
	"io/ioutil"
	"testing"
	"github.com/labstack/echo/v4"
	"github.com/stretchr/testify/mock"
	"github.com/stretchr/testify/assert"
)

type MockEventer struct {
	mock.Mock
}

func (m *MockEventer) Send (id string, url string) error {
	args := m.Called(id, url)
	return args.Error(0)
}

func TestGetEvent_forwardHttps(t *testing.T) {
	e := echo.New()

	expectedEvent := `{"user":"123","page":"789","event":{"type":"external","value":{"type":"linksniffer:click","url":"https://redcross.org"}}}`

	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		data, err := ioutil.ReadAll(r.Body)
		assert.Nil(t, err)
		assert.Equal(t, expectedEvent, string(data))
	}))

	q := make(url.Values)
	q.Set("url", "redcross.org")
	q.Set("id", "123")
	req := httptest.NewRequest(http.MethodGet, "/?"+q.Encode(), nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	client := &http.Client{}
	s := &Server{&Eventer{client, ts.URL, "789"}}

	s.forward(c)
	assert.Equal(t, http.StatusFound, rec.Code)
	assert.Equal(t, "https://redcross.org", rec.HeaderMap["Location"][0])
}


func TestGetEvent_forwardHttp(t *testing.T) {
	e := echo.New()

	expectedEvent := `{"user":"123","page":"789","event":{"type":"external","value":{"type":"linksniffer:click","url":"http://redcross.org"}}}`

	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		data, err := ioutil.ReadAll(r.Body)
		assert.Nil(t, err)
		assert.Equal(t, expectedEvent, string(data))
	}))

	q := make(url.Values)
	q.Set("url", "redcross.org")
	q.Set("id", "123")
	q.Set("p", "http")
	req := httptest.NewRequest(http.MethodGet, "/?"+q.Encode(), nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	client := &http.Client{}
	s := &Server{&Eventer{client, ts.URL, "789"}}

	s.forward(c)
	assert.Equal(t, http.StatusFound, rec.Code)
	assert.Equal(t, "http://redcross.org", rec.HeaderMap["Location"][0])
}
