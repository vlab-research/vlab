package main

import (
	"encoding/json"
	"net/http"
	"testing"
	"time"

	"github.com/vlab-research/go-reloadly/reloadly"
	"github.com/stretchr/testify/assert"
)

func TestGiftCardsResultsOnErrorIfBadDetails(t *testing.T) {
	ts := JSTimestamp(time.Now().UTC())
	jm := json.RawMessage([]byte(`{"foo": "bar"}`))
	pe := &PaymentEvent{
		Userid:    "foo",
		Pageid:    "page",
		Timestamp: &ts,
		Provider:  "reloadly-giftcard",
		Details:   &jm,
	}
	cfg := getConfig()
	pool := getPool(cfg)
	svc := &reloadly.Service{
		Client: &http.Client{},
	}
	rp := ReloadlyProvider{pool, svc, "INVALID_GIFT_CARD_DETAILS"}
	provider := &GiftCardsProvider{rp}
	res, err := provider.Payout(pe)

	assert.Nil(t, err)
	assert.NotNil(t, res.Error)
	assert.Equal(t, "INVALID_GIFT_CARD_DETAILS", res.Error.Code)
	assert.Equal(t, "payment:reloadly-giftcard", res.Type)
	assert.Equal(t, false, res.Success)
}

func TestGiftCardsReportsAPIErrorsInResult(t *testing.T) {
	ts := JSTimestamp(time.Now().UTC())
	jm := json.RawMessage([]byte(`{"productId":1234,"countryCode":"test-country","quantity":1,"unitPrice":0.5,"customIdentifier":"test-identifier","senderName":"test-name","recipientEmail":"test@test.com","id":"test-id"}`))
	pe := &PaymentEvent{
		Userid:    "foo",
		Pageid:    "page",
		Timestamp: &ts,
		Provider:  "reloadly-giftcard",
		Details:   &jm,
	}
	cfg := getConfig()
	pool := getPool(cfg)
	svc := &reloadly.Service{
		Client: TestClient(404, `{"errorCode": "FOOBAR", "message": "Sorry"}`, nil),
	}
	rp := ReloadlyProvider{pool, svc, ""}
	provider := &GiftCardsProvider{rp}
	res, err := provider.Payout(pe)

	assert.Nil(t, err)
	assert.NotNil(t, res.Error)
	assert.Equal(t, "FOOBAR", res.Error.Code)
	assert.Equal(t, "Sorry", res.Error.Message)
	assert.Equal(t, &jm, res.Error.PaymentDetails)
	assert.Equal(t, "test-id", res.ID)
	assert.Equal(t, "payment:reloadly-giftcard", res.Type)
	assert.Equal(t, false, res.Success)
}

func TestGiftCardsReportsSuccessResult(t *testing.T) {
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
	jm := json.RawMessage([]byte(`{"productId":1234,"countryCode":"test-country","quantity":1,"unitPrice":0.5,"customIdentifier":"test-identifier","senderName":"test-name","recipientEmail":"test@test.com","id":"test-id"}`))
	pe := &PaymentEvent{
		Userid:    "00000000-0000-0000-0000-000000000000",
		Pageid:    "page",
		Timestamp: &ts,
		Provider:  "reloadly-giftcard",
		Details:   &jm,
	}
	svc := &reloadly.Service{
		Client: TestClient(200, `{"transactionId":1,"amount":0.1,"discount":10,"currencyCode":"INR","fee":1,"recipientEmail":"test@test.com","customIdentifier":"test-card","status":"SUCCESSFUL","transactionCreatedTime":"2021-11-15 16:55:30"}`, nil),
	}
	rp := ReloadlyProvider{pool, svc, ""}
	provider := &GiftCardsProvider{rp}

	user, err := provider.GetUserFromPaymentEvent(pe)
	assert.Nil(t, err)
	assert.Equal(t, user.Id, "00000000-0000-0000-0000-000000000000")

	err = provider.Auth(user)
	assert.Nil(t, err)

	res, err := provider.Payout(pe)
	assert.Nil(t, err)
	assert.Nil(t, res.Error)
	assert.Equal(t, "payment:reloadly-giftcard", res.Type)
	assert.Equal(t, true, res.Success)
	assert.Equal(t, &jm, res.PaymentDetails)
}
