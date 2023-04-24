package users_test

import (
	"fmt"
	"testing"

	"github.com/stretchr/testify/require"
	"github.com/vlab-research/vlab/dashboard-api/internal/testhelpers"
)

func TestHandler_GetOrCreate(t *testing.T) {

	testcases := []struct {
		userID         string
		description    string
		expectedStatus int
		expectedRes    string
	}{
		{
			userID:         testhelpers.CurrentUserId,
			description:    "return 200 when user exists with user",
			expectedStatus: 200,
			expectedRes:    `{"data":{"id":"auth0|61916c1dab79c900713936de"}}`,
		},
		{
			userID:         "new-user",
			description:    "return 201 when user is created with user",
			expectedStatus: 201,
			expectedRes:    `{"data":{"id":"new-user"}}`,
		},
	}
	for _, tc := range testcases {
		t.Run(fmt.Sprintf("should  %s", tc.description),
			func(t *testing.T) {
				assert := require.New(t)
				testhelpers.DeleteAllUsers(t)
				testhelpers.CreateUser(t)
				res := getorCreateUserRequest(t, tc.userID)
				assert.Equal(res.StatusCode, tc.expectedStatus)
				assert.Equal(tc.expectedRes, res.Body)
			})
	}
}

func getorCreateUserRequest(t *testing.T, userID string) testhelpers.Response {
	t.Helper()
	r := testhelpers.GetRepositories()
	return testhelpers.PerformPostRequest(
		"/users",
		userID,
		r,
		nil,
	)
}
