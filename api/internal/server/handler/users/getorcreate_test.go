package users_test

import (
	"fmt"
	"testing"

	"github.com/stretchr/testify/require"
	"github.com/vlab-research/vlab/api/internal/testhelpers"
)

func TestHandler_GetOrCreate(t *testing.T) {

	testcases := []struct {
		userID         string
		description    string
		expectedStatus int
		expectedRes    []string
	}{
		{
			userID:         testhelpers.CurrentUserID,
			description:    "return 200 when user exists with user and orgs",
			expectedStatus: 201,
			expectedRes:    []string{`{"data":{"id":"auth0|61916c1dab79c900713936de","orgs":[{"id":"fda19390-d1e7-4893-a13a-d14c88cc737b","name":"auth0|61916c1dab79c900713936de"}]}}`},
		},
		{
			userID:         "new-user",
			description:    "return 201 when user is created with user and no orgs",
			expectedStatus: 201,
			expectedRes:    []string{`"id":"new-user"`, `"name":"new-user"`},
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
				for _, e := range tc.expectedRes {
					assert.Contains(res.Body, e)
				}
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
