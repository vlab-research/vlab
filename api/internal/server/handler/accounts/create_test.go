package accounts_test

import (
	"context"
	"fmt"
	"testing"
	"github.com/stretchr/testify/require"
	"github.com/vlab-research/vlab/api/internal/testhelpers"
	"github.com/vlab-research/vlab/api/internal/types"
)

func TestHandler_Account_Create(t *testing.T) {
	assert := require.New(t)
	userId := "auth0|61916c1dab79c900713936de"
	entity := "fly"
	authType := types.AccountType(entity)


	testcases := []struct {
		account        types.Account
		description    string
		expectedStatus int
		expectedRes    string
	}{
		{
			account: types.Account{
				UserID:   userId,
				Name:     "fly123",
				AuthType: authType,
				Account: []byte(`
					{
						"createdAt": null,
						"credentials": {
							"api_key": "supersecret"
						}
					}
					`),
			},
			expectedStatus: 201,
			expectedRes:    `{"data":{"userId":"auth0|61916c1dab79c900713936de","name":"fly123","authType":"fly","connectedAccount":{"createdAt":null,"credentials":{"api_key":"supersecret"}}}}`,
			description:    "return 200 for valid fly account",
		},
		{
			expectedStatus: 400,
			expectedRes:    `{"error":"Key: 'Account.AuthType' Error:Field validation for 'AuthType' failed on the 'required' tag"}`,
			description:    "return 400 for invalid fly account",
			account: types.Account{
				UserID: userId,
				Name:   "fly123",
				Account: []byte(`
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
			expectedRes:    `{"error":"Invalid is an unknown account type"}`,
			description:    "return 400 for unknown account type",
			account: types.Account{
				UserID: userId,
				Name:   "Invalid",
				Account: []byte(`
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
			expectedRes:    `{"data":{"userId":"auth0|61916c1dab79c900713936de","name":"typeform-test","authType":"typeform","connectedAccount":{"createdAt":null,"credentials":{"key":"supersecret"}}}}`,
			description:    "return 201 for valid typeform account",
			account: types.Account{
				UserID:   userId,
				Name:     "typeform-test",
				AuthType: authType,
				Account: []byte(`
					{
						"createdAt": null,
						"credentials": {
							"key": "supersecret"
						}
					}
					`),
			},
		},
		{
			expectedStatus: 201,
			expectedRes:    `{"data":{"userId":"auth0|61916c1dab79c900713936de","name":"alchemer*!","authType":"alchemer","connectedAccount":{"createdAt":null,"credentials":{"api_token":"supersecret","api_token_secret":"supersecret"}}}}`,
			description:    "return 201 for valid alchemer account",
			account: types.Account{
				UserID:   userId,
				Name:     "alchemer*!",
				AuthType: authType,
				Account: []byte(`
					{
						"createdAt": null,
						"credentials": {
							"api_token": "supersecret",
							"api_token_secret": "supersecret"
						}
					}
					`),
			},
		},
		{
			expectedStatus: 201,
			expectedRes:    `{"data":{"userId":"auth0|61916c1dab79c900713936de","name":"Facebook","authType":"facebook","connectedAccount":{"createdAt":null,"credentials":{"token":"supersecret"}}}}`,
			description:    "return 201 for valid Facebook account",
			account: types.Account{
				UserID:   userId,
				Name:     "Facebook",
				AuthType: authType,
				Account: []byte(`
					{
						"createdAt": null,
						"credentials": {
							"token": "supersecret",
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
	r.User.Create(context.TODO(), testhelpers.CurrentUserID)
	return testhelpers.PerformPostRequest(
		"/accounts",
		testhelpers.CurrentUserID,
		r,
		a,
	)
}
