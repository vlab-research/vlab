package studies

import (
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
	studiesmanager "github.com/vlab-research/vlab/dashboard-api/internal"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/storage/storagemocks"
)

func TestHandler_List(t *testing.T) {
	t.Run("should return a 200 with the requested studies when the repository returns them", func(t *testing.T) {
		defaultOffset := 0
		defaultLimit := 20
		studyRepository := new(storagemocks.StudyRepository)
		study := studiesmanager.NewStudy("5372ca9c-9fcd-42d4-a596-d90792909917", "Example Study", "example-study", 1605049200000)
		studyRepository.On("GetStudies", mock.Anything, defaultOffset, defaultLimit).Return([]studiesmanager.Study{study}, nil)

		res := performRequest("/studies", studyRepository)

		assert.Equal(t, http.StatusOK, res.StatusCode)
		assert.Equal(t, "application/json; charset=utf-8", res.Header.Get("Content-Type"))
		assert.Equal(t, "{\"data\":[{\"id\":\"5372ca9c-9fcd-42d4-a596-d90792909917\",\"name\":\"Example Study\",\"slug\":\"example-study\",\"createdAt\":1605049200000}],\"pagination\":{\"nextCursor\":null}}", res.body)
	})

	t.Run("should return a 400 when the cursor query parameter is invalid", func(t *testing.T) {
		res := performRequest("/studies?cursor=invalid-cursor", new(storagemocks.StudyRepository))

		assert.Equal(t, http.StatusBadRequest, res.StatusCode)
		assert.Equal(t, "application/json; charset=utf-8", res.Header.Get("Content-Type"))
		assert.Equal(t, "{\"error\":\"Key: 'paginationQueryParams.CursorInBase64url' Error:Field validation for 'CursorInBase64url' failed on the 'base64url' tag\"}", res.body)
	})

	t.Run("should return a 400 when the number query parameter is invalid", func(t *testing.T) {
		res := performRequest("/studies?number=101", new(storagemocks.StudyRepository))

		assert.Equal(t, http.StatusBadRequest, res.StatusCode)
		assert.Equal(t, "application/json; charset=utf-8", res.Header.Get("Content-Type"))
		assert.Equal(t, "{\"error\":\"Key: 'paginationQueryParams.Number' Error:Field validation for 'Number' failed on the 'lte' tag\"}", res.body)
	})

	t.Run("should return a 500 when the repository returns an error", func(t *testing.T) {
		studyRepository := new(storagemocks.StudyRepository)
		studyRepository.On("GetStudies", mock.Anything, mock.Anything, mock.Anything).Return([]studiesmanager.Study{}, errors.New("unexpected-error"))
		res := performRequest("/studies", studyRepository)

		assert.Equal(t, http.StatusInternalServerError, res.StatusCode)
	})

	t.Run("should return a valid nextCursor when number of studies returned for the current page is equal to the requested ones", func(t *testing.T) {
		numStudiesPerPage := 2
		studyRepository := new(storagemocks.StudyRepository)
		studyRepository.On("GetStudies", mock.Anything, 0, numStudiesPerPage).
			Return(
				[]studiesmanager.Study{
					studiesmanager.NewStudy("5372ca9c-9fcd-42d4-a596-d90792909917", "Example Study1", "example-study1", 1605049200000),
					studiesmanager.NewStudy("94259273-d64c-4e1f-9a67-9b283d5d84b5", "Example Study2", "example-study2", 1605049200000),
				},
				nil,
			)

		res := performRequest(fmt.Sprintf("/studies?number=%d", numStudiesPerPage), studyRepository)

		assert.Equal(t, http.StatusOK, res.StatusCode)
		assert.Equal(t, "application/json; charset=utf-8", res.Header.Get("Content-Type"))
		assert.Equal(t, "{\"data\":[{\"id\":\"5372ca9c-9fcd-42d4-a596-d90792909917\",\"name\":\"Example Study1\",\"slug\":\"example-study1\",\"createdAt\":1605049200000},{\"id\":\"94259273-d64c-4e1f-9a67-9b283d5d84b5\",\"name\":\"Example Study2\",\"slug\":\"example-study2\",\"createdAt\":1605049200000}],\"pagination\":{\"nextCursor\":\"Mg==\"}}", res.body)
	})

	t.Run("should return a null nextCursor when number of studies returned for the current page is less than the requested ones", func(t *testing.T) {
		numStudiesPerPage := 2
		studyRepository := new(storagemocks.StudyRepository)
		studyRepository.On("GetStudies", mock.Anything, 0, numStudiesPerPage).
			Return(
				[]studiesmanager.Study{
					studiesmanager.NewStudy("5372ca9c-9fcd-42d4-a596-d90792909917", "Example Study1", "example-study1", 1605049200000),
				},
				nil,
			)

		res := performRequest(fmt.Sprintf("/studies?number=%d", numStudiesPerPage), studyRepository)

		assert.Equal(t, http.StatusOK, res.StatusCode)
		assert.Equal(t, "application/json; charset=utf-8", res.Header.Get("Content-Type"))
		assert.Equal(t, "{\"data\":[{\"id\":\"5372ca9c-9fcd-42d4-a596-d90792909917\",\"name\":\"Example Study1\",\"slug\":\"example-study1\",\"createdAt\":1605049200000}],\"pagination\":{\"nextCursor\":null}}", res.body)
	})
}

type response struct {
	StatusCode int
	Header     http.Header
	body       string
}

func performRequest(path string, studyRepository studiesmanager.StudyRepository) response {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.GET("/studies", ListHandler(studyRepository))

	req, err := http.NewRequest(http.MethodGet, path, nil)
	if err != nil {
		log.Fatalf("(http.NewRequest) performRequest failed for path: %s", path)
	}

	rec := httptest.NewRecorder()
	r.ServeHTTP(rec, req)

	res := rec.Result()
	body, err := io.ReadAll(res.Body)
	if err != nil {
		log.Fatalf("(io.ReadAll) performRequest failed for path: %s", path)
	}

	defer res.Body.Close()

	return response{
		StatusCode: res.StatusCode,
		Header:     res.Header,
		body:       string(body),
	}
}
