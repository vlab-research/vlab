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
	"github.com/vlab-research/vlab/api/internal/config"
	"github.com/vlab-research/vlab/api/internal/server"
	"github.com/vlab-research/vlab/api/internal/storage"
	"github.com/vlab-research/vlab/api/internal/types"
)

const (
	CurrentUserID = "auth0|61916c1dab79c900713936de"
	StudySlug     = "test-study"
	TestOrgID     = "fda19390-d1e7-4893-a13a-d14c88cc737b"
)

type Response struct {
	StatusCode int
	Header     http.Header
	Body       string
}

func PerformGetRequest(path string, repositories storage.Repositories) Response {
	return PerformRequest(path, CurrentUserID, http.MethodGet, repositories, nil)
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

// TODO this depends on a package that we want to test
// using the testhelper, we should remove alle dependencies in this helper
// to avoid circular dependency errors
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
	repositories.Db.Exec("DELETE FROM orgs")
}

func CreateStudy(t *testing.T, slug, userID string) error {
	t.Helper()
	r := GetRepositories()
	q := "INSERT INTO studies (id, slug, name, user_id, org_id) VALUES ($1, $2, $3, $4, $5)"
	_, err := r.Db.Exec(q, StudyID, slug, slug, userID, TestOrgID)
	return err
}

func CreateStudyFromStudy(t *testing.T, study types.Study) error {
	t.Helper()
	r := GetRepositories()
	q := "INSERT INTO studies (id, slug, name, user_id, org_id, created) VALUES ($1, $2, $3, $4, $5, $6)"
	_, err := r.Db.Exec(
		q,
		study.ID,
		study.Slug,
		study.Name,
		CurrentUserID,
		TestOrgID,
		time.Unix(study.CreatedAt, 0),
	)
	return err
}

func CreateUser(t *testing.T) {
	t.Helper()
	r := GetRepositories()
	_, _ = r.Db.Exec("INSERT INTO orgs (id, name) VALUES ($1, $2)", TestOrgID, CurrentUserID)
	q := "INSERT INTO users (id) VALUES ($1)"
	_, _ = r.Db.Exec(q, CurrentUserID)
	q = "INSERT INTO orgs_lookup (user_id, org_id) VALUES ($1, $2)"
	_, _ = r.Db.Exec(q, CurrentUserID, TestOrgID)
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
