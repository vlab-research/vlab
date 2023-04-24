package testhelpers

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	jwtmiddleware "github.com/auth0/go-jwt-middleware/v2"
	"github.com/auth0/go-jwt-middleware/v2/validator"
	"github.com/gin-gonic/gin"
	"github.com/vlab-research/vlab/dashboard-api/internal/config"
	"github.com/vlab-research/vlab/dashboard-api/internal/server"
	"github.com/vlab-research/vlab/dashboard-api/internal/storage"
	"github.com/vlab-research/vlab/dashboard-api/internal/types"
)

const (
	CurrentUserId = "auth0|61916c1dab79c900713936de"
	StudySlug     = "test-study"
)

type Response struct {
	StatusCode int
	Header     http.Header
	Body       string
}

func PerformGetRequest(path string, repositories storage.Repositories) Response {
	return PerformRequest(path, CurrentUserId, http.MethodGet, repositories, nil)
}

func PerformPostRequest(
	path, userID string,
	repositories storage.Repositories,
	body interface{},
) Response {
	return PerformRequest(path, userID, http.MethodPost, repositories, body)
}

func PerformDeleteRequest(
	path, userID string,
	repositories storage.Repositories,
	body interface{},
) Response {
	return PerformRequest(path, userID, http.MethodDelete, repositories, body)
}

func PerformRequest(
	path, userID string,
	method string,
	repositories storage.Repositories,
	body interface{},
) Response {

	gin.SetMode(gin.TestMode)
	a, teardown := GetFBTestApp()
	defer teardown()

	cfg, _ := config.Setup()
	srv := server.Server{
		Cfg:            cfg,
		FacebookApp:    a,
		Repos:          repositories,
		AuthMiddleware: FakeValidTokenMiddleware(userID),
	}

	srv.GetRouter()

	var req *http.Request
	var err error

	if method != http.MethodGet {
		reqBodyAsString, _ := json.Marshal(body)
		req, err = http.NewRequest(
			method,
			path,
			bytes.NewBuffer([]byte(reqBodyAsString)),
		)
	} else {
		req, err = http.NewRequest(method, path, nil)
	}
	if err != nil {
		log.Fatalf("(http.NewRequest) performRequest failed for path: %s", path)
	}

	rec := httptest.NewRecorder()
	srv.Handler.ServeHTTP(rec, req)

	res := rec.Result()
	resBody, err := io.ReadAll(res.Body)
	if err != nil {
		log.Fatalf("(io.ReadAll) performRequest failed for path: %s", path)
	}

	defer res.Body.Close()

	return Response{
		StatusCode: res.StatusCode,
		Header:     res.Header,
		Body:       string(resBody),
	}
}

func FakeValidTokenMiddleware(userID string) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		userCtx := validator.ValidatedClaims{
			RegisteredClaims: validator.RegisteredClaims{
				Subject: userID,
			},
		}

		ctx.Request = ctx.Request.Clone(
			context.WithValue(ctx.Request.Context(), jwtmiddleware.ContextKey{}, &userCtx),
		)

		ctx.Next()
	}
}

func GetRepositories() storage.Repositories {
	//TODO we should probably set some environment variables here
	//that testing depends on in order for tests to have less external
	//dependencies
	cfg, err := config.Setup()
	if err != nil {
		log.Fatal(err)
	}
	return storage.InitializeRepositories(cfg.DB)
}

func DeleteAllStudies(t *testing.T) {
	t.Helper()
	repositories := GetRepositories()
	repositories.Db.Exec("DELETE FROM studies")
}

func DeleteAllAccounts(t *testing.T) {
	t.Helper()
	repositories := GetRepositories()
	repositories.Db.Exec("DELETE FROM credentials")
}

func DeleteAllUsers(t *testing.T) {
	t.Helper()
	repositories := GetRepositories()
	repositories.Db.Exec("DELETE FROM users")
}

func CreateStudy(t *testing.T, slug, userID string) error {
	t.Helper()
	r := GetRepositories()
	q := "INSERT INTO studies (id, slug, name, user_id) VALUES ($1, $2, $3, $4)"
	_, err := r.Db.Exec(q, StudyID, slug, slug, userID)
	return err
}

func CreateUser(t *testing.T) {
	t.Helper()
	r := GetRepositories()
	_, _ = r.Db.Exec("INSERT INTO users (id) VALUES ($1)", CurrentUserId)
}

func CreateAccounts(t *testing.T, a types.Account, created time.Time) error {
	t.Helper()
	var c string
	var err error
	var i interface{}
	if a.ConnectedAccount != i {
		c, err = a.ConnectedAccount.MarshalCredentials()
		if err != nil {
			return err
		}
	} else {
		c = "{}"
	}
	r := GetRepositories()
	q := "INSERT INTO credentials (user_id, entity, key, details, created) VALUES ($1, $2, $3, $4, $5)"
	_, err = r.Db.Exec(q, a.UserID, a.Name, a.AuthType, c, created)
	return err
}
