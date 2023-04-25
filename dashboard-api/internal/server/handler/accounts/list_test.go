package accounts_test

import (
	"context"
	"fmt"
	"testing"
	"time"

	"github.com/stretchr/testify/require"
	"github.com/vlab-research/vlab/dashboard-api/internal/storage"
	"github.com/vlab-research/vlab/dashboard-api/internal/testhelpers"
	"github.com/vlab-research/vlab/dashboard-api/internal/types"
	sourcetypes "github.com/vlab-research/vlab/inference/sources/types"
)

func TestHandler_Account_List(t *testing.T) {
	assert := require.New(t)

	authType := "token"
	created := time.Date(2020, time.November, 10, 23, 0, 0, 0, time.UTC)
	testcases := []struct {
		accounts       []types.Account
		description    string
		expectedStatus int
		//because of timezone issues we  cant do exact matching
		//so we just check that response contains a list of
		//characters
		expectedRes []string
	}{
		{
			accounts: []types.Account{
				{
					UserID:   testhelpers.CurrentUserId,
					Name:     "Fly",
					AuthType: authType,
					ConnectedAccount: types.FlyConnectedAccount{
						Credentials: sourcetypes.FlyCredentials{
							APIKey: "supersecret",
						},
					},
				},
				{
					UserID:   testhelpers.CurrentUserId,
					Name:     "Typeform",
					AuthType: authType,
					ConnectedAccount: types.TypeformConnectedAccount{
						Credentials: sourcetypes.TypeformCredentials{
							Key: "supersecret",
						},
					},
				},
				{
					UserID:   testhelpers.CurrentUserId,
					Name:     "Alchemer",
					AuthType: authType,
					ConnectedAccount: types.AlchemerConnectedAccount{
						Credentials: sourcetypes.AlchemerCreds{
							ApiToken:       "supersecret",
							ApiTokenSecret: "supersecret",
						},
					},
				},
			},
			expectedStatus: 200,
			expectedRes:    []string{`{"key":"supersecret"}`, `{"api_key":"supersecret"}`, `{"api_token":"supersecret","api_token_secret":"supersecret"}`},
			description:    "return 200 with a list of accounts",
		},
		{
			accounts:       []types.Account{},
			expectedStatus: 200,
			expectedRes:    []string{`"data":[]`},
			description:    "return 200 with no data",
		},
	}

	for _, tc := range testcases {
		t.Run(fmt.Sprintf("should %s", tc.description),
			func(t *testing.T) {
				testhelpers.DeleteAllUsers(t)
				testhelpers.DeleteAllAccounts(t)
				testhelpers.CreateUser(t)
				for _, a := range tc.accounts {
					err := testhelpers.CreateAccounts(t, a, created)
					assert.NoError(err)
				}
				res := listAccountRequest()
				for _, expected := range tc.expectedRes {
					assert.Contains(res.Body, expected)
				}
				assert.Equal(res.StatusCode, tc.expectedStatus)
			})
	}

}

func listAccountRequest() testhelpers.Response {
	r := testhelpers.GetRepositories()
	r.User.Create(context.TODO(), testhelpers.CurrentUserId)
	return testhelpers.PerformGetRequest(
		"/accounts",
		storage.Repositories{
			Account: testhelpers.GetRepositories().Account,
		},
	)
}
