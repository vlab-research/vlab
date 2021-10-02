package main

import (
	"encoding/json"
	"net/http"
	"testing"
	"time"

	"github.com/nandanrao/go-reloadly/reloadly"
	"github.com/stretchr/testify/assert"
)

func before() {
	http.Get("http://system/resetdb")
}

func TestReloadlyResultsOnErrorIfBadDetails(t *testing.T) {
	ts := JSTimestamp(time.Now().UTC())
	jm := json.RawMessage([]byte(`{"foo": "bar"}`))
	pe := &PaymentEvent{
		Userid:    "foo",
		Pageid:    "page",
		Timestamp: &ts,
		Provider:  "reloadly",
		Details:   &jm,
	}
	cfg := getConfig()
	pool := getPool(cfg)
	svc := &reloadly.Service{
		Client: &http.Client{},
	}
	provider := &ReloadlyProvider{pool, svc}
	res, err := provider.Payout(pe)

	assert.Nil(t, err)
	assert.NotNil(t, res.Error)
	assert.Equal(t, "INVALID_PAYMENT_DETAILS", res.Error.Code)
	assert.Equal(t, "payment:reloadly", res.Type)
	assert.Equal(t, false, res.Success)
}

func TestReloadlyReportsAPIErrorsInResult(t *testing.T) {
	ts := JSTimestamp(time.Now().UTC())
	jm := json.RawMessage([]byte(`{"number": "+123", "amount": 2.5, "country": "IN", "id": "id"}`))
	pe := &PaymentEvent{
		Userid:    "foo",
		Pageid:    "page",
		Timestamp: &ts,
		Provider:  "reloadly",
		Details:   &jm,
	}
	cfg := getConfig()
	pool := getPool(cfg)
	svc := &reloadly.Service{
		Client: TestClient(404, `{"errorCode": "FOOBAR", "message": "Sorry"}`, nil),
	}
	provider := &ReloadlyProvider{pool, svc}
	res, err := provider.Payout(pe)

	assert.Nil(t, err)
	assert.NotNil(t, res.Error)
	assert.Equal(t, "FOOBAR", res.Error.Code)
	assert.Equal(t, "Sorry", res.Error.Message)
	assert.Equal(t, &jm, res.Error.PaymentDetails)
	assert.Equal(t, "id", res.ID)
	assert.Equal(t, "payment:reloadly", res.Type)
	assert.Equal(t, false, res.Success)
}

func TestReloadlyReportsSuccessResult(t *testing.T) {
	before()

	cfg := getConfig()
	pool := getPool(cfg)
	defer pool.Close()

	insertUserSql := `
		INSERT INTO users(id, email) 
		VALUES ('00000000-0000-0000-0000-000000000000', 'test@test.com');
	`
	mustExec(t, pool, insertUserSql)
	insertFbPageSql := `
		INSERT INTO credentials(userid, entity, key, details)
		VALUES ('00000000-0000-0000-0000-000000000000', 'facebook_page', 'test-key', '{"id": "page"}');
	`
	mustExec(t, pool, insertFbPageSql)
	insertReloadlySql := `
		INSERT INTO credentials(userid, entity, key, details)
		VALUES ('00000000-0000-0000-0000-000000000000', 'reloadly', 'test-key', '{"id": "test-id", "secret": "test-secret"}');
	`
	mustExec(t, pool, insertReloadlySql)

	ts := JSTimestamp(time.Now().UTC())
	jm := json.RawMessage([]byte(`{"number": "+123", "amount": 2.5, "country": "IN"}`))
	pe := &PaymentEvent{
		Userid:    "00000000-0000-0000-0000-000000000000",
		Pageid:    "page",
		Timestamp: &ts,
		Provider:  "reloadly",
		Details:   &jm,
	}
	svc := &reloadly.Service{
		Client: TestClient(200, `{"suggestedAmountsMap":{"2.5": 2.5},"transactionDate":"2020-09-19 12:53:22","transactionId": 567}`, nil),
	}
	provider := &ReloadlyProvider{pool, svc}

	user, err := provider.GetUserFromPaymentEvent(pe)
	assert.Nil(t, err)
	assert.Equal(t, user.Id, "00000000-0000-0000-0000-000000000000")

	err = provider.Auth(user)
	assert.Nil(t, err)

	res, err := provider.Payout(pe)
	assert.Nil(t, err)
	assert.Nil(t, res.Error)
	assert.Equal(t, "payment:reloadly", res.Type)
	assert.Equal(t, true, res.Success)
	assert.Equal(t, &jm, res.PaymentDetails)
}

func TestReloadlyResultsOnMissingUser(t *testing.T) {
	before()

	cfg := getConfig()
	pool := getPool(cfg)
	defer pool.Close()

	svc := &reloadly.Service{}
	provider := &ReloadlyProvider{pool, svc}
	pe := &PaymentEvent{
		Pageid: "page",
	}
	user, err := provider.GetUserFromPaymentEvent(pe)
	assert.Nil(t, user)
	assert.Nil(t, err)
}

func TestReloadlyResultsOnMissingCredentials(t *testing.T) {
	before()

	cfg := getConfig()
	pool := getPool(cfg)
	defer pool.Close()

	insertUserSql := `
		INSERT INTO users(id, email) 
		VALUES ('00000000-0000-0000-0000-000000000000', 'test@test.com');
	`
	mustExec(t, pool, insertUserSql)
	insertFbPageSql := `
		INSERT INTO credentials(userid, entity, key, details)
		VALUES ('00000000-0000-0000-0000-000000000000', 'facebook_page', 'test-key', '{"id": "page"}');
	`
	mustExec(t, pool, insertFbPageSql)

	svc := &reloadly.Service{}
	provider := &ReloadlyProvider{pool, svc}
	pe := &PaymentEvent{
		Pageid: "page",
	}
	user, err := provider.GetUserFromPaymentEvent(pe)
	assert.NotNil(t, user)
	assert.Nil(t, err)

	err = provider.Auth(user)
	assert.Equal(t, err.Error(), "No credentials were found for user: 00000000-0000-0000-0000-000000000000")
}
