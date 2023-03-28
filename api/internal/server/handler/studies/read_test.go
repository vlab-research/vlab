package studies_test

import (
	"context"
	"fmt"
	"testing"

	"github.com/stretchr/testify/require"
	"github.com/vlab-research/vlab/api/internal/testhelpers"
	"github.com/vlab-research/vlab/api/internal/types"
)

// TODO remove all these mocks for actual integration tests
func TestHandler_Read(t *testing.T) {

	assert := require.New(t)
	testcases := []struct {
		study          types.Study
		description    string
		slug           string
		expectedStatus int
		expectedRes    []string
	}{
		{
			description: "return a 200 with with the requested study",
			study: types.Study{
				ID:        "5372ca9c-9fcd-42d4-a596-d90792909917",
				Name:      "Example Study",
				Slug:      "example-study",
				CreatedAt: 1605049200000,
			},
			slug:           "example-study",
			expectedRes:    []string{`"id":"5372ca9c-9fcd-42d4-a596-d90792909917","name":"Example Study","slug":"example-study"`},
			expectedStatus: 200,
		},
		{
			description: "return a 404 when study does not exist",
			study: types.Study{
				ID:        "5372ca9c-9fcd-42d4-a596-d90792909917",
				Name:      "Example Study",
				Slug:      "example-study",
				CreatedAt: 1605049200000,
			},
			slug:           "not-found",
			expectedRes:    []string{`{"error":"Study not found: not-found"}`},
			expectedStatus: 404,
		},
	}
	for _, tc := range testcases {
		t.Run(fmt.Sprintf("should %s", tc.description),
			func(t *testing.T) {
				testhelpers.DeleteAllStudies(t)
				testhelpers.DeleteAllUsers(t)
				testhelpers.CreateUser(t)
				err := testhelpers.CreateStudyFromStudy(t, tc.study)
				assert.NoError(err)
				res := getStudyRequest(t, tc.slug)
				assert.Equal(res.StatusCode, tc.expectedStatus)
				for _, e := range tc.expectedRes {
					assert.Contains(res.Body, e)
				}
			})
	}
}

func getStudyRequest(t *testing.T, slug string) testhelpers.Response {
	t.Helper()
	r := testhelpers.GetRepositories()
	r.User.Create(context.TODO(), testhelpers.CurrentUserID)
	return testhelpers.PerformGetRequest(
		fmt.Sprintf("/%s/studies/%s", testhelpers.TestOrgID, slug),
		r,
	)
}
