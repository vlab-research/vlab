package main

import (
	"io/ioutil"
	"net/http"
	"net/http/httptest"
	"net/url"
	"testing"

	"github.com/labstack/echo/v4"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
)

type MockEventer struct {
	mock.Mock
}

func (m *MockEventer) Send(id string, url string) error {
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
	q.Set("pageid", "789")
	req := httptest.NewRequest(http.MethodGet, "/?"+q.Encode(), nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	client := &http.Client{}
	s := &Server{&Eventer{client, ts.URL}}

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
	q.Set("pageid", "789")
	req := httptest.NewRequest(http.MethodGet, "/?"+q.Encode(), nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	client := &http.Client{}
	s := &Server{&Eventer{client, ts.URL}}

	s.forward(c)
	assert.Equal(t, http.StatusFound, rec.Code)
	assert.Equal(t, "http://redcross.org", rec.HeaderMap["Location"][0])
}

func TestGetEvent_errorsOnLackingID(t *testing.T) {
	e := echo.New()

	q := make(url.Values)
	q.Set("url", "redcross.org")

	req := httptest.NewRequest(http.MethodGet, "/?"+q.Encode(), nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	client := &http.Client{}
	s := &Server{&Eventer{client, ""}}

	err := s.forward(c)
	assert.Equal(t, 400, err.(*echo.HTTPError).Code)
}
