package studies_test

import (
	"errors"
	"net/http"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
	studiesmanager "github.com/vlab-research/vlab/dashboard-api/internal"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/storage"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/storage/storagemocks"
	"github.com/vlab-research/vlab/dashboard-api/internal/testhelpers"
)

func TestHandler_Read(t *testing.T) {
	t.Run("should return a 404 when the requested study does not exist", func(t *testing.T) {
		studyRepository := new(storagemocks.StudyRepository)
		studyRepository.On("GetStudyBySlug", mock.Anything, "example-study", mock.Anything).Return(studiesmanager.Study{}, studiesmanager.ErrStudyNotFound)

		res := testhelpers.PerformGetRequest("/studies/example-study", storage.Repositories{Study: studyRepository})

		assert.Equal(t, http.StatusNotFound, res.StatusCode)
		assert.Equal(t, "application/json; charset=utf-8", res.Header.Get("Content-Type"))
		assert.Equal(t, "{\"error\":\"Study not found\"}", res.Body)
	})

	t.Run("should return a 500 when there is an error while processing the request", func(t *testing.T) {
		studyRepository := new(storagemocks.StudyRepository)
		studyRepository.On("GetStudyBySlug", mock.Anything, "example-study", mock.Anything).Return(studiesmanager.Study{}, errors.New("db timeout error"))

		res := testhelpers.PerformGetRequest("/studies/example-study", storage.Repositories{Study: studyRepository})

		assert.Equal(t, http.StatusInternalServerError, res.StatusCode)
	})

	t.Run("should return a 200 with with the requested study when it exists", func(t *testing.T) {
		studyRepository := new(storagemocks.StudyRepository)
		study := studiesmanager.NewStudy("5372ca9c-9fcd-42d4-a596-d90792909917", "Example Study", "example-study", 1605049200000)
		studyRepository.On("GetStudyBySlug", mock.Anything, "example-study", mock.Anything).Return(study, nil)

		res := testhelpers.PerformGetRequest("/studies/example-study", storage.Repositories{Study: studyRepository})

		assert.Equal(t, http.StatusOK, res.StatusCode)
		assert.Equal(t, "application/json; charset=utf-8", res.Header.Get("Content-Type"))
		assert.Equal(t, "{\"data\":{\"id\":\"5372ca9c-9fcd-42d4-a596-d90792909917\",\"name\":\"Example Study\",\"slug\":\"example-study\",\"createdAt\":1605049200000}}", res.Body)
	})
}
