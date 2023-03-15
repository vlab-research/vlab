package testhelpers

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"net/http/httptest"

	jwtmiddleware "github.com/auth0/go-jwt-middleware/v2"
	"github.com/auth0/go-jwt-middleware/v2/validator"
	"github.com/gin-gonic/gin"
	"github.com/vlab-research/vlab/dashboard-api/cmd/api/bootstrap"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/server"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/storage"
)

var CurrentUserId = "auth0|61916c1dab79c900713936de"

type Response struct {
	StatusCode int
	Header     http.Header
	Body       string
}

func PerformGetRequest(path string, repositories storage.Repositories) Response {
	return PerformRequest(path, http.MethodGet, repositories, nil)
}

func PerformPostRequest(
	path string,
	repositories storage.Repositories,
	body interface{},
) Response {
	return PerformRequest(path, http.MethodPost, repositories, body)
}

func PerformRequest(
	path string,
	method string,
	repositories storage.Repositories,
	body interface{},
) Response {
	gin.SetMode(gin.TestMode)

	noopString := ""
	noopUint := uint(0)

	srv := server.New(
		noopString,
		noopUint,
		repositories,
		FakeValidTokenMiddleware(),
		noopString,
	)
	var req *http.Request
	var err error

	if method == http.MethodPost {
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
	srv.Engine.ServeHTTP(rec, req)

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

func FakeValidTokenMiddleware() gin.HandlerFunc {
	return func(ctx *gin.Context) {
		userCtx := validator.ValidatedClaims{
			RegisteredClaims: validator.RegisteredClaims{
				Subject: CurrentUserId,
			},
		}

		ctx.Request = ctx.Request.Clone(
			context.WithValue(ctx.Request.Context(), jwtmiddleware.ContextKey{}, &userCtx),
		)

		ctx.Next()
	}
}

func GetRepositories() storage.Repositories {
	cfg, err := bootstrap.GetConfig()
	if err != nil {
		log.Fatal(err)
	}
	return storage.InitializeRepositories(cfg.DB)
}

func DeleteAllStudies() {
	repositories := GetRepositories()
	repositories.Db.Exec("DELETE FROM studies")
}

func DeleteAllAccounts() {
	repositories := GetRepositories()
	repositories.Db.Exec("DELETE FROM credentials")
}

func DeleteAllStudyConfs() {
	repositories := GetRepositories()
	repositories.Db.Exec("DELETE FROM study_conf")
}

func DeleteAllUsers() {
	repositories := GetRepositories()
	repositories.Db.Exec("DELETE FROM users")
}

func CreateStudy(slug, userID string) error {
	r := GetRepositories()
	q := "INSERT INTO studies (slug, name, user_id) VALUES ($1, $2, $3)"
	_, err := r.Db.Exec(q, slug, slug, userID)
	return err
}

func CreateUser() {
	r := GetRepositories()
	_, _ = r.Db.Exec("INSERT INTO users (id) VALUES ($1)", CurrentUserId)
}
