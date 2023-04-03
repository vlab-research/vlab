package studies_test

import (
	"context"
	"errors"
	"fmt"
	"math/rand"
	"testing"

	"github.com/stretchr/testify/mock"
	"github.com/stretchr/testify/require"
	studiesmanager "github.com/vlab-research/vlab/dashboard-api/internal"
	"github.com/vlab-research/vlab/dashboard-api/internal/storage"
	"github.com/vlab-research/vlab/dashboard-api/internal/storage/storagemocks"
	"github.com/vlab-research/vlab/dashboard-api/internal/testhelpers"
)

func TestHandler_Create(t *testing.T) {
	assert := require.New(t)
	errorString := "{\"error\":\"%s\"}"
	expectedHeader := "application/json; charset=utf-8"

	t.Run("should return a 400 when no name is provided", func(t *testing.T) {
		msg := "The name cannot be empty."

		res := createStudyRequest("")
		assert.Equal(400, res.StatusCode)
		assert.Equal(expectedHeader, res.Header.Get("Content-Type"))
		assert.Equal(fmt.Sprintf(errorString, msg), res.Body)
	})
	t.Run("should return 400 with only whitespace", func(t *testing.T) {
		msg := "The name cannot be empty."
		res := createStudyRequest("   ")
		assert.Equal(400, res.StatusCode)
		assert.Equal(expectedHeader, res.Header.Get("Content-Type"))
		assert.Equal(fmt.Sprintf(errorString, msg), res.Body)
	})
	t.Run("should return a 400 error when over length limit", func(t *testing.T) {
		size := 301
		msg := "The name cannot be larger than 300 characters."

		res := createStudyRequest(randStringRunes(size))
		assert.Equal(400, res.StatusCode)
		assert.Equal(expectedHeader, res.Header.Get("Content-Type"))
		assert.Equal(fmt.Sprintf(errorString, msg), res.Body)
	})

	t.Run("should return a 201 with the created study", func(t *testing.T) {
		testhelpers.DeleteAllStudies(t)
		studyName := "example study"

		res := createStudyRequest(studyName)

		assert.Contains(res.Body, studyName)
		assert.Equal(201, res.StatusCode)
		assert.Equal(expectedHeader, res.Header.Get("Content-Type"))
	})

	t.Run("should return a 409 when the study already exists", func(t *testing.T) {
		testhelpers.DeleteAllStudies(t)
		studyName := "example study"
		msg := "The name is already in use."
		res := createStudyRequest(studyName)
		assert.Equal(201, res.StatusCode)

		res = createStudyRequest(studyName)
		assert.Equal(409, res.StatusCode)
		assert.Equal(fmt.Sprintf(errorString, msg), res.Body)
	})

	t.Run("should return a 500 when the studyRepository returns an unexpected error", func(t *testing.T) {
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

		assert.Equal(500, res.StatusCode)
	})
}

func createStudyRequest(studyName string) testhelpers.Response {
	r := testhelpers.GetRepositories()
	r.User.CreateUser(context.TODO(), testhelpers.CurrentUserId)
	return testhelpers.PerformPostRequest(
		"/studies",
		storage.Repositories{
			Study: testhelpers.GetRepositories().Study,
		},
		struct {
			Name string `json:"name"`
		}{studyName},
	)
}

var letterRunes = []rune("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")

func randStringRunes(n int) string {
	b := make([]rune, n)
	for i := range b {
		b[i] = letterRunes[rand.Intn(len(letterRunes))]
	}
	return string(b)
}
