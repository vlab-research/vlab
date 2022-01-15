package testhelpers

import (
	"context"
	"io"
	"log"
	"net/http"
	"net/http/httptest"

	jwtmiddleware "github.com/auth0/go-jwt-middleware"
	"github.com/auth0/go-jwt-middleware/validate/josev2"
	"github.com/gin-gonic/gin"
	"gopkg.in/square/go-jose.v2/jwt"

	"github.com/vlab-research/vlab/dashboard-api/internal/platform/server"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/storage"
)

type response struct {
	StatusCode int
	Header     http.Header
	Body       string
}

func PerformGetRequest(path string, repositories storage.Repositories) response {
	return PerformRequest(path, http.MethodGet, repositories)
}

func PerformPostRequest(path string, repositories storage.Repositories, body interface{}) response {
	return PerformRequest(path, http.MethodPost, repositories)
}

func PerformRequest(path string, method string, repositories storage.Repositories) response {
	gin.SetMode(gin.TestMode)

	noopString := ""
	noopUint := uint(0)

	srv := server.New(noopString, noopUint, repositories, FakeValidTokenMiddleware(), noopString)

	req, err := http.NewRequest(method, path, nil)
	if err != nil {
		log.Fatalf("(http.NewRequest) performRequest failed for path: %s", path)
	}

	rec := httptest.NewRecorder()
	srv.Engine.ServeHTTP(rec, req)

	res := rec.Result()
	body, err := io.ReadAll(res.Body)
	if err != nil {
		log.Fatalf("(io.ReadAll) performRequest failed for path: %s", path)
	}

	defer res.Body.Close()

	return response{
		StatusCode: res.StatusCode,
		Header:     res.Header,
		Body:       string(body),
	}
}

func FakeValidTokenMiddleware() gin.HandlerFunc {
	return func(ctx *gin.Context) {
		userCtx := josev2.UserContext{
			RegisteredClaims: jwt.Claims{
				Subject: "fake-user-id",
			},
		}

		ctx.Request = ctx.Request.Clone(context.WithValue(ctx.Request.Context(), jwtmiddleware.ContextKey{}, &userCtx))

		ctx.Next()
	}
}
