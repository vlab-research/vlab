package testhelpers

import (
	"io"
	"log"
	"net/http"
	"net/http/httptest"

	"github.com/gin-gonic/gin"

	"github.com/vlab-research/vlab/dashboard-api/internal/platform/server"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/storage"
)

type response struct {
	StatusCode int
	Header     http.Header
	Body       string
}

func PerformGetRequest(path string, repositories storage.Repositories) response {
	gin.SetMode(gin.TestMode)

	ignoredHost := "ignored"
	ignoredPort := 0
	srv := server.New(ignoredHost, uint(ignoredPort), repositories)

	req, err := http.NewRequest(http.MethodGet, path, nil)
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
