package facebook_test

import (
	"context"
	"fmt"
	"testing"

	"github.com/stretchr/testify/require"
	"github.com/vlab-research/vlab/dashboard-api/internal/storage"
	"github.com/vlab-research/vlab/dashboard-api/internal/testhelpers"
)

func TestGenerateTokenHandler(t *testing.T) {
	assert := require.New(t)
	testcases := []struct {
		code           string
		description    string
		expectedStatus int
		expectedRes    string
	}{
		{
			description:    "201 with valid code",
			code:           "valid",
			expectedStatus: 201,
			expectedRes:    `{"data":{"userId":"auth0|61916c1dab79c900713936de","authType":"bearer","name":"facebook","connectedAccount":{"createdAt":"0001-01-01T00:00:00Z","credentials":{"expires_in":5181452,"access_token":"supersecret","token_type":"bearer"}}}}`,
		},
		{
			description:    "400 with invalid code",
			code:           "invalid",
			expectedStatus: 400,
			expectedRes:    `{"error":"facebook: fail to parse facebook response with error facebook: empty response from facebook"}`,
		},
	}
	for _, tc := range testcases {
		t.Run(fmt.Sprintf("should  %s", tc.description),
			func(t *testing.T) {
				res := generateTokenRequest(t, tc.code)
				assert.Equal(tc.expectedRes, res.Body)
				assert.Equal(tc.expectedStatus, res.StatusCode)
			})
	}
}

func generateTokenRequest(t *testing.T, code string) testhelpers.Response {
	t.Helper()
	r := testhelpers.GetRepositories()
	r.User.CreateUser(context.TODO(), testhelpers.CurrentUserId)
	return testhelpers.PerformPostRequest(
		"/facebook/token",
		storage.Repositories{
			Account: testhelpers.GetRepositories().Account,
		},
		struct {
			Code string `json:"code"`
		}{code},
	)
}