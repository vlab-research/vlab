package users_test

import (
	"errors"
	"net/http"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
	studiesmanager "github.com/vlab-research/vlab/dashboard-api/internal"
	"github.com/vlab-research/vlab/dashboard-api/internal/storage"
	"github.com/vlab-research/vlab/dashboard-api/internal/storage/storagemocks"
	"github.com/vlab-research/vlab/dashboard-api/internal/testhelpers"
)

func TestHandler_Read(t *testing.T) {
	t.Run("should return a 422 when the user already exists", func(t *testing.T) {
		userRepository := new(storagemocks.UserRepository)
		userRepository.On("CreateUser", mock.Anything, mock.Anything).Return(studiesmanager.User{}, studiesmanager.ErrUserAlreadyExists)

		res := testhelpers.PerformPostRequest("/users", storage.Repositories{User: userRepository}, nil)

		assert.Equal(t, http.StatusUnprocessableEntity, res.StatusCode)
		assert.Equal(t, "application/json; charset=utf-8", res.Header.Get("Content-Type"))
		assert.Equal(t, "{\"error\":\"User already exists\"}", res.Body)
	})

	t.Run("should return a 500 when there is an error while processing the request", func(t *testing.T) {
		userRepository := new(storagemocks.UserRepository)
		userRepository.On("CreateUser", mock.Anything, mock.Anything).Return(studiesmanager.User{}, errors.New("db timeout error"))

		res := testhelpers.PerformPostRequest("/users", storage.Repositories{User: userRepository}, nil)

		assert.Equal(t, http.StatusInternalServerError, res.StatusCode)
	})

	t.Run("should return a 201 with the created user", func(t *testing.T) {
		userRepository := new(storagemocks.UserRepository)
		userRepository.On("CreateUser", mock.Anything, mock.Anything).Return(studiesmanager.User{Id: "auth0|61916c1dab79c900713936de"}, nil)

		res := testhelpers.PerformPostRequest("/users", storage.Repositories{User: userRepository}, nil)

		assert.Equal(t, http.StatusCreated, res.StatusCode)
		assert.Equal(t, "application/json; charset=utf-8", res.Header.Get("Content-Type"))
		assert.Equal(t, "{\"data\":{\"id\":\"auth0|61916c1dab79c900713936de\"}}", res.Body)
	})
}
