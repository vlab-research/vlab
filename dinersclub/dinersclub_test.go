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

const (
	insertUserSql = `INSERT INTO users(id, email) VALUES ($1, $2);`
	insertCredentialsSql = `
		INSERT INTO credentials(userid, entity, key, details)
		VALUES ($1, 'fake', $2, '{"id": "", "secret": ""}');
	`
)

func before() {
	http.Get("http://system/resetdb")
}

func TestDinersClub(t *testing.T) {
	before()
	count := 0

	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		expected := []string{
			`{"user":"00000000-0000-0000-0000-000000000000","page":"page","event":{"type":"external","value":{"type":"foo","success":true,"timestamp":"0001-01-01T00:00:00Z"}}}`,
			`{"user":"33333333-3333-3333-3333-333333333333","page":"page","event":{"type":"external","value":{"type":"foo","success":true,"timestamp":"0001-01-01T00:00:00Z"}}}`,
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

	mustExec(t, pool, insertUserSql, "00000000-0000-0000-0000-000000000000", "000@test.com")
	mustExec(t, pool, insertCredentialsSql, "00000000-0000-0000-0000-000000000000", "test-key-0")
	mustExec(t, pool, insertUserSql, "33333333-3333-3333-3333-333333333333", "333@test.com")
	mustExec(t, pool, insertCredentialsSql, "33333333-3333-3333-3333-333333333333", "test-key-3")

	providers, _ := getProviders(cfg)
	dc := DC{cfg, pool, providers, &botparty.BotParty{Client: http.DefaultClient, Botserver: ts.URL}}

	msgs := makeMessages([]string{
		`{
			"userid": "00000000-0000-0000-0000-000000000000",
			"pageid": "page",
			"timestamp": 1600558963867,
			"provider": "fake",
			"details": {
				"result": {
					"type": "foo",
					"success": true
				}
			}
		}`,
		`{
			"userid": "33333333-3333-3333-3333-333333333333",
			"pageid": "page",
			"timestamp": 1600558963867,
			"provider": "fake",
			"details": {
				"result": {
					"type": "foo",
					"success": true
				}
			}
		}`,
	})

	err := dc.Process(msgs)
	assert.Nil(t, err)
}

func TestDinersClubErrorsOnMessagesWithMissingFields(t *testing.T) {
	before()

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
		`{
			"userid": "foo",
			"pageid": "page",
			"timestamp": 1600558963867,
			"details": {
				"result": {
					"type": "foo",
					"success": true
				}
			}
		}`,
	})

	err := dc.Process(msgs)
	assert.NotNil(t, err)
	e := err.(validator.ValidationErrors)
	assert.Contains(t, e.Error(), "Provider")
}

func TestDinersClubErrorsOnMalformedJSONMessages(t *testing.T) {
	before()

	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {}))

	cfg := getConfig()
	cfg.PoolSize = 2
	cfg.Providers = []string{"fake"}
	pool := getPool(cfg)
	providers, _ := getProviders(cfg)
	dc := DC{cfg, pool, providers, &botparty.BotParty{Client: http.DefaultClient, Botserver: ts.URL}}

	msgs := makeMessages([]string{
		`{
			"userid": "foo",
			"pageid": "page",
			"timestamp"---> invalid-syntax <-----
			"details": {
				"result": {
					"type": "foo",
					"success": true
				}
			}
		}`,
	})

	err := dc.Process(msgs)
	assert.NotNil(t, err)

	e := err.(*json.SyntaxError)
	assert.Contains(t, e.Error(), "invalid character")
}

func TestDinersClubErrorsOnNonExistentProvider(t *testing.T) {
	before()

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
		`{
			"userid": "foo",
			"pageid": "page",
			"provider": "baz",
			"timestamp": 1600558963867,
			"details": {
				"result": {
					"type": "foo",
					"success": true
				}
			}
		}`,
	})

	err := dc.Process(msgs)
	assert.Nil(t, err)
}

func TestDinersClubRepeatsOnServerErrorFromBotserver(t *testing.T) {
	before()
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

	mustExec(t, pool, insertUserSql, "00000000-0000-0000-0000-000000000000", "test@test.com")
	mustExec(t, pool, insertCredentialsSql, "00000000-0000-0000-0000-000000000000", "test-key")

	providers, _ := getProviders(cfg)
	dc := DC{cfg, pool, providers, &botparty.BotParty{Client: http.DefaultClient, Botserver: ts.URL}}

	msgs := makeMessages([]string{
		`{
			"userid": "00000000-0000-0000-0000-000000000000",
			"pageid": "page",
			"timestamp": 1600558963867,
			"provider": "fake",
			"details": {
				"result": {
					"type": "foo",
					"success": true
				}
			}
		}`,
	})

	err := dc.Process(msgs)
	assert.NotNil(t, err)
	assert.Contains(t, err.Error(), "Botserver")
	assert.Equal(t, 3, count)
}

func TestDinersClubRepeatsOnErrorFromProviderPayout(t *testing.T) {
	before()

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
		`{
			"userid": "foo",
			"pageid": "page",
			"timestamp": 1600558963867,
			"provider": "mock",
			"details": {
				"error": true
			}
		}`,
	})

	err := dc.Process(msgs)
	t.Log(err)
	assert.NotNil(t, err)
	assert.Contains(t, err.Error(), "mock error")
	assert.Equal(t, 3, provider.count)
}

func TestDinersClubErrorsOnMissingCredentials(t *testing.T) {
	before()

	cfg := getConfig()
	cfg.Providers = []string{"fake"}
	pool := getPool(cfg)
	providers, _ := getProviders(cfg)
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {}))
	dc := DC{cfg, pool, providers, &botparty.BotParty{Client: http.DefaultClient, Botserver: ts.URL}}

	msgs := makeMessages([]string{
		`{
			"userid": "00000000-0000-0000-0000-000000000000",
			"pageid": "page",
			"timestamp": 1600558963867,
			"provider": "fake",
			"details": {
				"result": {
					"type": "foo",
					"success": true
				}
			}
		}`,
	})

	err := dc.Process(msgs)
	assert.NotNil(t, err)
	assert.Equal(t, err.Error(), "No credentials were found to authorize the user")
}
