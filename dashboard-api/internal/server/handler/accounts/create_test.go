package accounts_test

import (
	"context"
	"fmt"
	"testing"

	"github.com/stretchr/testify/require"
	studiesmanager "github.com/vlab-research/vlab/dashboard-api/internal"
	"github.com/vlab-research/vlab/dashboard-api/internal/storage"
	"github.com/vlab-research/vlab/dashboard-api/internal/testhelpers"
)

func TestHandler_Account_Create(t *testing.T) {
	assert := require.New(t)
	userId := "auth0|61916c1dab79c900713936de"
	authType := "token"

	testcases := []struct {
		account        studiesmanager.Account
		description    string
		expectedStatus int
		expectedRes    string
	}{
		{
			account: studiesmanager.Account{
				UserID:   userId,
				Name:     "Fly",
				AuthType: authType,
				RawConnectedAccount: []byte(`
					{
						"createdAt": null,
						"credentials": {
							"api_key": "supersecret"
						}
					}
					`),
			},
			expectedStatus: 201,
			expectedRes:    "{\"data\":{\"id\":\"\",\"userId\":\"auth0|61916c1dab79c900713936de\",\"authType\":\"token\",\"name\":\"Fly\",\"connectedAccount\":{\"createdAt\":null,\"credentials\":{\"api_key\":\"supersecret\"}}}}",
			description:    "return 200 for valid fly account",
		},
		{
			expectedStatus: 400,
			expectedRes:    "{\"error\":\"Key: 'Account.AuthType' Error:Field validation for 'AuthType' failed on the 'required' tag\"}",
			description:    "return 400 for invalid fly account",
			account: studiesmanager.Account{
				UserID: userId,
				Name:   "Fly",
				RawConnectedAccount: []byte(`
					{
						"createdAt": null,
						"credentials": {
							"api_key": "supersecret"
						}
					}
					`),
			},
		},
		{
			expectedStatus: 400,
			expectedRes:    "{\"error\":\"unknown account type Invalid\"}",
			description:    "return 400 for unknown account type",
			account: studiesmanager.Account{
				UserID: userId,
				Name:   "Invalid",
				RawConnectedAccount: []byte(`
					{
						"createdAt": null,
						"credentials": {
							"api_key": "supersecret"
						}
					}
					`),
			},
		},
		{
			expectedStatus: 201,
			expectedRes:    "{\"data\":{\"id\":\"\",\"userId\":\"auth0|61916c1dab79c900713936de\",\"authType\":\"token\",\"name\":\"Typeform\",\"connectedAccount\":{\"createdAt\":null,\"credentials\":{\"key\":\"supersecret\"}}}}",
			description:    "return 201 for valid typeform account",
			account: studiesmanager.Account{
				UserID:   userId,
				Name:     "Typeform",
				AuthType: authType,
				RawConnectedAccount: []byte(`
					{
						"createdAt": null,
						"credentials": {
							"key": "supersecret"
						}
					}
					`),
			},
		},
	}

	for _, tc := range testcases {
		t.Run(fmt.Sprintf("should  %s", tc.description),
			func(t *testing.T) {
				testhelpers.DeleteAllAccounts(t)
				res := createAccountRequest(t, tc.account)
				assert.Contains(res.Body, tc.expectedRes)
				assert.Equal(res.StatusCode, tc.expectedStatus)
			})
	}

}

func createAccountRequest(t *testing.T, a interface{}) testhelpers.Response {
	t.Helper()
	r := testhelpers.GetRepositories()
	r.User.CreateUser(context.TODO(), testhelpers.CurrentUserId)
	return testhelpers.PerformPostRequest(
		"/accounts",
		storage.Repositories{
			Account: testhelpers.GetRepositories().Account,
		},
		a,
	)
}
