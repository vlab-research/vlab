package studies_test

import (
	"errors"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
	studiesmanager "github.com/vlab-research/vlab/dashboard-api/internal"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/storage"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/storage/storagemocks"
	"github.com/vlab-research/vlab/dashboard-api/internal/testhelpers"
)

func TestHandler_Create(t *testing.T) {
	t.Run("should return a 400 when no name is provided", func(t *testing.T) {
		testhelpers.DeleteAllStudies()

		res := createStudyRequest("")
		assert.Equal(t, 400, res.StatusCode)
		assert.Equal(t, "application/json; charset=utf-8", res.Header.Get("Content-Type"))
		assert.Equal(t, "{\"error\":\"The name cannot be empty.\"}", res.Body)

		res = createStudyRequest("   ")
		assert.Equal(t, 400, res.StatusCode)
		assert.Equal(t, "application/json; charset=utf-8", res.Header.Get("Content-Type"))
		assert.Equal(t, "{\"error\":\"The name cannot be empty.\"}", res.Body)
	})

	t.Run("should return a 400 error when name provided is very large", func(t *testing.T) {
		testhelpers.DeleteAllStudies()

		res := createStudyRequest("verylargenameeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
		assert.Equal(t, 400, res.StatusCode)
		assert.Equal(t, "application/json; charset=utf-8", res.Header.Get("Content-Type"))
		assert.Equal(t, "{\"error\":\"The name cannot be larger than 300 characters.\"}", res.Body)
	})

	t.Run("should return a 201 with the created study", func(t *testing.T) {
		testhelpers.DeleteAllStudies()
		studyName := "example study"

		res := createStudyRequest(studyName)

		assert.Equal(t, 201, res.StatusCode)
		assert.Equal(t, "application/json; charset=utf-8", res.Header.Get("Content-Type"))
		assert.Contains(t, res.Body, studyName)
	})

	t.Run("should return a 409 when the study already exists", func(t *testing.T) {
		testhelpers.DeleteAllStudies()
		studyName := "example study"

		res := createStudyRequest(studyName)
		assert.Equal(t, 201, res.StatusCode)

		res = createStudyRequest(studyName)
		assert.Equal(t, 409, res.StatusCode)
		assert.Equal(t, "{\"error\":\"The name is already in use.\"}", res.Body)
	})

	t.Run("should return a 500 when the studyRepository returns an unexpected error", func(t *testing.T) {
		testhelpers.DeleteAllStudies()
		studyName := "example study"
		studyRepository := new(storagemocks.StudyRepository)
		studyRepository.On("CreateStudy", mock.Anything, mock.Anything, mock.Anything).Return(studiesmanager.Study{}, errors.New("unexpected-error"))

		res := testhelpers.PerformPostRequest(
			"/studies",
			storage.Repositories{Study: studyRepository},
			struct {
				Name string `json:"name"`
			}{studyName},
		)

		assert.Equal(t, 500, res.StatusCode)
	})
}

func createStudyRequest(studyName string) testhelpers.Response {
	return testhelpers.PerformPostRequest(
		"/studies",
		storage.Repositories{Study: testhelpers.GetRepositories().Study},
		struct {
			Name string `json:"name"`
		}{studyName},
	)
}
