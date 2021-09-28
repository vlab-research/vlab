package main

import (
	"encoding/json"
	"io/ioutil"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/go-playground/validator/v10"
	"github.com/stretchr/testify/assert"
	"github.com/vlab-research/botparty"
)

func TestDinersClub(t *testing.T) {
	count := 0

	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		expected := []string{
			`{"user":"foo","page":"page","event":{"type":"external","value":{"type":"foo","success":true,"timestamp":"0001-01-01T00:00:00Z"}}}`,
			`{"user":"bar","page":"page","event":{"type":"external","value":{"type":"foo","success":true,"timestamp":"0001-01-01T00:00:00Z"}}}`,
		}

		data, _ := ioutil.ReadAll(r.Body)
		dat := strings.TrimSpace(string(data))

		good := dat == expected[0] || dat == expected[1]
		assert.True(t, good)

		assert.Equal(t, "/", r.URL.Path)
		w.WriteHeader(200)
		count++
	}))

	cfg := getConfig()
	cfg.Providers = []string{"fake"}
	pool := getPool(cfg)
	providers, _ := getProviders(cfg)
	dc := DC{cfg, pool, providers, &botparty.BotParty{Client: http.DefaultClient, Botserver: ts.URL}}

	msgs := makeMessages([]string{
		`{"userid": "foo",
          "pageid": "page",
          "timestamp": 1600558963867,
          "provider": "fake",
          "details": {"result": {"type": "foo", "success":true}}}`,
		`{"userid": "bar",
          "pageid": "page",
          "timestamp": 1600558963867,
          "provider": "fake",
          "details": {"result": {"type": "foo", "success":true}}}`,
	})

	err := dc.Process(msgs)
	assert.Nil(t, err)
}

func TestDinersClubErrorsOnMessagesWithMissingFields(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		assert.FailNow(t, "should not call botserver")
	}))

	cfg := getConfig()
	cfg.PoolSize = 2
	cfg.Providers = []string{"fake"}
	pool := getPool(cfg)
	providers, _ := getProviders(cfg)
	dc := DC{cfg, pool, providers, &botparty.BotParty{Client: http.DefaultClient, Botserver: ts.URL}}

	msgs := makeMessages([]string{
		`{"userid": "foo",
          "pageid": "page",
          "timestamp": 1600558963867,
          "details": {"result": {"type": "foo", "success":true}}}`,
	})

	err := dc.Process(msgs)
	assert.NotNil(t, err)
	e := err.(validator.ValidationErrors)
	assert.Contains(t, e.Error(), "Provider")
}

func TestDinersClubErrorsOnMalformedJSONMessages(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {}))

	cfg := getConfig()
	cfg.PoolSize = 2
	cfg.Providers = []string{"fake"}
	pool := getPool(cfg)
	providers, _ := getProviders(cfg)
	dc := DC{cfg, pool, providers, &botparty.BotParty{Client: http.DefaultClient, Botserver: ts.URL}}

	msgs := makeMessages([]string{
		`{"userid": "foo",
          "pageid": "page",
          "timestamp"1600558963867
          "details": {"result": {"type": "foo", "success":true}}}`,
	})

	err := dc.Process(msgs)
	assert.NotNil(t, err)

	e := err.(*json.SyntaxError)
	assert.Contains(t, e.Error(), "invalid character")
}

func TestDinersClubErrorsOnNonExistentProvider(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		data, _ := ioutil.ReadAll(r.Body)
		dat := strings.TrimSpace(string(data))
		assert.Contains(t, dat, `"code":"INVALID_PROVIDER"`)
		assert.Contains(t, dat, "baz")
		assert.Equal(t, "/", r.URL.Path)
		w.WriteHeader(200)
	}))

	cfg := getConfig()
	cfg.PoolSize = 2
	cfg.Providers = []string{"fake"}
	pool := getPool(cfg)
	providers, _ := getProviders(cfg)
	dc := DC{cfg, pool, providers, &botparty.BotParty{Client: http.DefaultClient, Botserver: ts.URL}}

	msgs := makeMessages([]string{
		`{"userid": "foo",
          "pageid": "page",
          "provider": "baz",
          "timestamp": 1600558963867,
          "details": {"result": {"type": "foo", "success":true}}}`,
	})

	err := dc.Process(msgs)
	assert.Nil(t, err)
}

func TestDinersClubRepeatsOnServerErrorFromBotserver(t *testing.T) {
	count := 0

	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		count++

		assert.Equal(t, "/", r.URL.Path)
		w.WriteHeader(500)
	}))

	cfg := getConfig()
	cfg.PoolSize = 2
	cfg.Providers = []string{"fake"}
	cfg.RetryBotserver = 1 * time.Second
	pool := getPool(cfg)
	providers, _ := getProviders(cfg)
	dc := DC{cfg, pool, providers, &botparty.BotParty{Client: http.DefaultClient, Botserver: ts.URL}}

	msgs := makeMessages([]string{
		`{"userid": "foo",
          "pageid": "page",
          "timestamp": 1600558963867,
          "provider": "fake",
          "details": {"result": {"type": "foo", "success":true}}}`,
	})

	err := dc.Process(msgs)
	assert.NotNil(t, err)
	assert.Contains(t, err.Error(), "Botserver")
	assert.Equal(t, 3, count)
}

func TestDinersClubRepeatsOnErrorFromProviderPayout(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		assert.FailNow(t, "Should not have called botserver")
	}))

	cfg := getConfig()
	cfg.PoolSize = 2
	cfg.RetryProvider = 1 * time.Second
	pool := getPool(cfg)
	provider := &MockErrorProvider{}
	providers := map[string]Provider{"mock": provider}
	dc := DC{cfg, pool, providers, &botparty.BotParty{Client: http.DefaultClient, Botserver: ts.URL}}

	msgs := makeMessages([]string{
		`{"userid": "foo",
          "pageid": "page",
          "timestamp": 1600558963867,
          "provider": "mock",
          "details": {"error": true}}`,
	})

	err := dc.Process(msgs)
	t.Log(err)
	assert.NotNil(t, err)
	assert.Contains(t, err.Error(), "mock error")
	assert.Equal(t, 3, provider.count)
}
