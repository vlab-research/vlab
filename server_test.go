package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/labstack/echo/v4"
	"github.com/stretchr/testify/assert"
	"github.com/vlab-research/trans"
)

const (
	surveySql = `drop table if exists surveys;
                 create table if not exists surveys(
                   userid VARCHAR NOT NULL,
                   id VARCHAR NOT NULL UNIQUE,
                   form_json JSON,
                   created TIMESTAMPTZ NOT NULL,
                   translation_conf JSON
                 );`

	insertSql = `INSERT INTO surveys(userid, created, id, form_json) VALUES ('owner', NOW(), $1, $2);`

	formA = `{"fields": [
          {"title": "What is your gender? ",
           "ref": "eng_foo",
           "properties": {
              "choices": [{"label": "Male"},
                          {"label": "Female"},
                          {"label": "Other"}]},
           "type": "multiple_choice"},
          {"title": "Which state do you currently live in?\n- A. foo 91  bar\n- B. Jharkhand\n- C. Odisha\n- D. Uttar Pradesh",
           "ref": "eng_bar",
           "properties": {"choices": [{"label": "A"},
                                      {"label": "B"},
                                      {"label": "C"},
                                      {"label": "D"}]},
           "type": "multiple_choice"},
           {"title": "How old are you?",
           "ref": "eng_baz",
           "properties": {},
           "type": "number"}]}`

	formB = `{"title": "mytitle", "fields": [
          {"id": "vjl6LihKMtcX",
          "title": "आपका लिंग क्या है? ",
          "ref": "foo",
          "properties": {"choices": [{"label": "पुरुष"},
                                    {"label": "महिला"},
                                    {"label": "अन्य"}]},
          "type": "multiple_choice"},
          {"id": "mdUpJMSY8Lct",
           "title": "वर्तमान में आप किस राज्य में रहते हैं?\n- A. छत्तीसगढ़\n- B. झारखंड\n- C. ओडिशा\n- D. उत्तर प्रदेश",
           "ref": "bar",
           "properties": {"choices": [{"label": "A"},
                                      {"label": "B"},
                                      {"label": "C"},
                                      {"label": "D"}]},
           "type": "multiple_choice"},
          {"id": "mdUpJMSY8Lct",
           "title": "वर्तमान में आप किस राज्य में रहते हैं?",
           "ref": "baz",
           "properties": {},
           "type": "number"}]}`
)

func TestTranslatorReturns404IfDestinationNotFound(t *testing.T) {
	pool := testPool()
	defer pool.Close()
	mustExec(t, pool, surveySql)

	request := fmt.Sprintf(`{"destination": "foo","form": %v}`, formA)
	body := bytes.NewReader([]byte(request))

	req := httptest.NewRequest(http.MethodPost, "/translator", body)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	c := echo.New().NewContext(req, rec)
	s := &Server{pool}

	err := s.CreateTranslator(c)
	assert.Equal(t, err.(*echo.HTTPError).Code, 404)
}

func TestTranslatorReturns400IfNotTranslatable(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	f := `{"title": "mytitle", "fields": [
          {"id": "vjl6LihKMtcX",
          "title": "आपका लिंग क्या है? ",
          "ref": "foo",
          "properties": {"choices": [{"label": "पुरुष"},
                                    {"label": "महिला"},
                                    {"label": "अन्य"}]},
          "type": "multiple_choice"},
          {"id": "mdUpJMSY8Lct",
           "title": "वर्तमान में आप किस राज्य में रहते हैं?",
           "ref": "baz",
           "properties": {},
           "type": "number"}]}`

	mustExec(t, pool, surveySql)
	mustExec(t, pool, insertSql, "foo", f)

	request := fmt.Sprintf(`{"destination": "foo","form": %v}`, formA)
	body := bytes.NewReader([]byte(request))

	req := httptest.NewRequest(http.MethodPost, "/translator", body)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	c := echo.New().NewContext(req, rec)
	s := &Server{pool}

	err := s.CreateTranslator(c)
	assert.Equal(t, err.(*echo.HTTPError).Code, 400)
}

func TestTranslatorReturnsTranslator(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, surveySql)
	mustExec(t, pool, insertSql, "foo", formB)

	request := fmt.Sprintf(`{"destination": "foo","form": %v}`, formA)
	body := bytes.NewReader([]byte(request))

	req := httptest.NewRequest(http.MethodPost, "/translator", body)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	c := echo.New().NewContext(req, rec)
	s := &Server{pool}

	err := s.CreateTranslator(c)
	assert.Nil(t, err)

	assert.Equal(t, http.StatusOK, rec.Code)

	ft := new(trans.FormTranslator)
	json.Unmarshal([]byte(rec.Body.String()), ft)
	assert.True(t, ft.Fields["eng_foo"].Translate)
}

func TestTranslatorWorksWithSelf(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, surveySql)

	request := fmt.Sprintf(`{"self": true,"form": %v}`, formA)
	body := bytes.NewReader([]byte(request))

	req := httptest.NewRequest(http.MethodPost, "/translator", body)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	c := echo.New().NewContext(req, rec)
	s := &Server{pool}

	err := s.CreateTranslator(c)
	assert.Nil(t, err)

	assert.Equal(t, http.StatusOK, rec.Code)

	ft := new(trans.FormTranslator)
	json.Unmarshal([]byte(rec.Body.String()), ft)
	assert.Equal(t, "Jharkhand", ft.Fields["eng_bar"].Mapping["B"])
}

func TestGetTranslatorGetsFromID(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, surveySql)
	mustExec(t, pool, insertSql, "bar", formB)

	insertWithTranslation := `INSERT INTO surveys(userid, created, id, form_json, translation_conf) VALUES ('owner', NOW(), $1, $2, $3);`
	mustExec(t, pool, insertWithTranslation, "foo", formA, `{"destination": "bar"}`)

	req := httptest.NewRequest(http.MethodGet, "/translator/foo", nil)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	c := echo.New().NewContext(req, rec)
	c.SetParamNames("surveyid")
	c.SetParamValues("foo")

	s := &Server{pool}

	err := s.GetTranslator(c)
	assert.Nil(t, err)
	assert.Equal(t, http.StatusOK, rec.Code)

	ft := new(trans.FormTranslator)
	json.Unmarshal([]byte(rec.Body.String()), ft)
	assert.True(t, ft.Fields["eng_foo"].Translate)
	assert.Equal(t, "पुरुष", ft.Fields["eng_foo"].Mapping["Male"])
}

func TestGetTranslatorGetsSelf(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, surveySql)
	mustExec(t, pool, insertSql, "bar", formB)

	insertWithTranslation := `INSERT INTO surveys(userid, created, id, form_json, translation_conf) VALUES ('owner', NOW(), $1, $2, $3);`
	mustExec(t, pool, insertWithTranslation, "foo", formA, `{"self": true}`)

	req := httptest.NewRequest(http.MethodGet, "/translator/foo", nil)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	c := echo.New().NewContext(req, rec)
	c.SetParamNames("surveyid")
	c.SetParamValues("foo")

	s := &Server{pool}

	err := s.GetTranslator(c)
	assert.Nil(t, err)
	assert.Equal(t, http.StatusOK, rec.Code)

	ft := new(trans.FormTranslator)
	json.Unmarshal([]byte(rec.Body.String()), ft)
	assert.True(t, ft.Fields["eng_foo"].Translate)
	assert.Equal(t, "Jharkhand", ft.Fields["eng_bar"].Mapping["B"])
}

func TestGetTranslatorReturns404OnRawTranslationConf(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, surveySql)
	mustExec(t, pool, insertSql, "bar", formB)

	insertWithTranslation := `INSERT INTO surveys(userid, created, id, form_json, translation_conf) VALUES ('owner', NOW(), $1, $2, $3);`
	mustExec(t, pool, insertWithTranslation, "foo", formA, `{}`)

	req := httptest.NewRequest(http.MethodGet, "/translator/foo", nil)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	c := echo.New().NewContext(req, rec)
	c.SetParamNames("surveyid")
	c.SetParamValues("foo")

	s := &Server{pool}

	err := s.GetTranslator(c)
	assert.Equal(t, err.(*echo.HTTPError).Code, 404)
}

func TestGetTranslatorReturns404OnMissingSourceForm(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	mustExec(t, pool, surveySql)
	mustExec(t, pool, insertSql, "bar", formB)

	insertWithTranslation := `INSERT INTO surveys(userid, created, id, form_json, translation_conf) VALUES ('owner', NOW(), $1, $2, $3);`
	mustExec(t, pool, insertWithTranslation, "foo", formA, `{}`)

	req := httptest.NewRequest(http.MethodGet, "/translator/foo", nil)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	c := echo.New().NewContext(req, rec)
	c.SetParamNames("surveyid")
	c.SetParamValues("baz")

	s := &Server{pool}

	err := s.GetTranslator(c)
	assert.Equal(t, err.(*echo.HTTPError).Code, 404)
}

func TestGetTranslatorReturns500OnTranslationError(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	smallForm := `{"title": "mytitle", "fields": [
          {"id": "vjl6LihKMtcX",
          "title": "आपका लिंग क्या है? ",
          "ref": "foo",
          "properties": {"choices": [{"label": "पुरुष"},
                                    {"label": "महिला"},
                                    {"label": "अन्य"}]},
          "type": "multiple_choice"},
          {"id": "mdUpJMSY8Lct",
           "title": "वर्तमान में आप किस राज्य में रहते हैं?",
           "ref": "baz",
           "properties": {},
           "type": "number"}]}`

	mustExec(t, pool, surveySql)
	mustExec(t, pool, insertSql, "qux", smallForm)

	insertWithTranslation := `INSERT INTO surveys(userid, created, id, form_json, translation_conf) VALUES ('owner', NOW(), $1, $2, $3);`
	mustExec(t, pool, insertWithTranslation, "foo", formA, `{"destination": "qux"}`)

	req := httptest.NewRequest(http.MethodGet, "/translator/foo", nil)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	c := echo.New().NewContext(req, rec)
	c.SetParamNames("surveyid")
	c.SetParamValues("foo")

	s := &Server{pool}

	err := s.GetTranslator(c)
	assert.Equal(t, err.(*echo.HTTPError).Code, 500)
}
