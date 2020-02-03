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

func TestGetEvent(t *testing.T) {
	e := echo.New()

	expectedEvent := `{"user":"123","event":{"type":"external","value":{"type":"linksniffer:click","url":"https://redcross.org"}}}`

	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		data, err := ioutil.ReadAll(r.Body)
		assert.Nil(t, err)
		assert.Equal(t, expectedEvent, string(data))
	}))

	q := make(url.Values)
	q.Set("url", "https%3A%2F%2Fredcross.org")
	q.Set("id", "123")
	req := httptest.NewRequest(http.MethodPost, "/?"+q.Encode(), nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	client := &http.Client{}
	s := &Server{&Eventer{client, ts.URL}}

	s.forward(c)
	assert.Equal(t, http.StatusFound, rec.Code)
	assert.Equal(t, "https://redcross.org", rec.HeaderMap["Location"][0])
}
