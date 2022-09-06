package accounts_test

import (
	"context"
	"fmt"
	"testing"

	"github.com/stretchr/testify/require"
	"github.com/vlab-research/vlab/dashboard-api/internal/storage"
	"github.com/vlab-research/vlab/dashboard-api/internal/testhelpers"
	"github.com/vlab-research/vlab/dashboard-api/internal/types"
)

func TestHandler_Account_Create(t *testing.T) {
	assert := require.New(t)
	userId := "auth0|61916c1dab79c900713936de"
	authType := "token"

	testcases := []struct {
		account        types.Account
		description    string
		expectedStatus int
		expectedRes    string
	}{
		{
			account: types.Account{
				UserID:   userId,
				Name:     "fly",
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
			expectedRes:    `{"data":{"userId":"auth0|61916c1dab79c900713936de","authType":"token","name":"fly","connectedAccount":{"createdAt":null,"credentials":{"api_key":"supersecret"}}}}`,
			description:    "return 200 for valid fly account",
		},
		{
			expectedStatus: 400,
			expectedRes:    `{"error":"Key: 'Account.AuthType' Error:Field validation for 'AuthType' failed on the 'required' tag"}`,
			description:    "return 400 for invalid fly account",
			account: types.Account{
				UserID: userId,
				Name:   "fly",
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
			expectedRes:    `{"error":"unknown account type Invalid"}`,
			description:    "return 400 for unknown account type",
			account: types.Account{
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
			expectedRes:    `{"data":{"userId":"auth0|61916c1dab79c900713936de","authType":"token","name":"typeform","connectedAccount":{"createdAt":null,"credentials":{"key":"supersecret"}}}}`,
			description:    "return 201 for valid typeform account",
			account: types.Account{
				UserID:   userId,
				Name:     "typeform",
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
				assert.Contains(tc.expectedRes, res.Body)
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
