package accounts_test

import (
	"context"
	"fmt"
	"testing"
	"time"
	"github.com/stretchr/testify/require"
	"github.com/vlab-research/vlab/api/internal/testhelpers"
	"github.com/vlab-research/vlab/api/internal/types"
)

func TestHandler_Account_Delete(t *testing.T) {
	assert := require.New(t)
	entity := "fly"
	authType := types.AccountType(entity)
	created := time.Date(2020, time.November, 10, 23, 0, 0, 0, time.UTC)
	testcases := []struct {
		account        types.Account
		userID         string
		description    string
		expectedStatus int
		expectedRes    string
	}{
		{
			account: types.Account{
				UserID:   testhelpers.CurrentUserID,
				Name:     "fly123",
				AuthType: authType,
			},
			userID:         testhelpers.CurrentUserID,
			expectedStatus: 204,
			description:    "return 204 with no content",
			expectedRes:    ``,
		},
		{
			account: types.Account{
				UserID:   testhelpers.CurrentUserID,
				Name:     "fly123",
				AuthType: authType,
			},
			userID:         "fake-user",
			expectedStatus: 404,
			description:    "return 404 if user cant access account",
			expectedRes:    `{"error":"account does not exist"}`,
		},
	}

	for _, tc := range testcases {
		t.Run(fmt.Sprintf("should %s", tc.description),
			func(t *testing.T) {
				testhelpers.DeleteAllUsers(t)
				testhelpers.DeleteAllAccounts(t)
				testhelpers.CreateUser(t)
				err := testhelpers.CreateAccounts(t, tc.account, created)
				assert.NoError(err)
				res := deleteAccountRequest(t, tc.account, tc.userID)
				assert.Equal(res.StatusCode, tc.expectedStatus)
				assert.Equal(res.Body, tc.expectedRes)
			})
	}

}

func deleteAccountRequest(t *testing.T, a types.Account, uid string) testhelpers.Response {
	t.Helper()
	r := testhelpers.GetRepositories()
	r.User.Create(context.TODO(), uid)
	return testhelpers.PerformDeleteRequest("/accounts", uid, r, a)
}
