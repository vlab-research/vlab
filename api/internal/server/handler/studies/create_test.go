package studies_test

import (
	"context"
	"fmt"
	"math/rand"
	"testing"

	"github.com/stretchr/testify/require"
	"github.com/vlab-research/vlab/api/internal/testhelpers"
)

func TestHandler_Create(t *testing.T) {
	assert := require.New(t)

	testcases := []struct {
		studyName      string
		description    string
		expectedStatus int
		expectedRes    string
	}{
		{
			description:    "should return a 400 when no name is provided",
			studyName:      "",
			expectedStatus: 400,
			expectedRes:    `{"error":"The name cannot be empty."}`,
		},
		{
			description:    "should return a 400 with whitespaces",
			studyName:      "	",
			expectedStatus: 400,
			expectedRes:    `{"error":"The name cannot be empty."}`,
		},
		{
			description:    "should return a 400 when over size limit",
			studyName:      randStringRunes(301),
			expectedStatus: 400,
			expectedRes:    `{"error":"The name cannot be larger than 300 characters."}`,
		},
		{
			description:    "return a 201 with the created study",
			studyName:      "example study",
			expectedStatus: 201,
			expectedRes:    `"name":"example study","slug":"example-study"`,
		},
		{
			description:    "return a 409 when the study already exists",
			studyName:      "duplicate-study",
			expectedStatus: 409,
			expectedRes:    `{"error":"The name is already in use."}`,
		},
	}

	for _, tc := range testcases {
		t.Run(fmt.Sprintf("should  %s", tc.description),
			func(t *testing.T) {
				testhelpers.DeleteAllStudies(t)
				err := testhelpers.CreateStudy(
					t,
					"duplicate-study",
					testhelpers.CurrentUserID,
				)
				assert.NoError(err)
				res := createStudyRequest(tc.studyName)
				assert.Contains(res.Body, tc.expectedRes)
				assert.Equal(res.StatusCode, tc.expectedStatus)
			})
	}

}

func createStudyRequest(studyName string) testhelpers.Response {
	r := testhelpers.GetRepositories()
	r.User.Create(context.TODO(), testhelpers.CurrentUserID)
	uri := fmt.Sprintf("/%s/studies", testhelpers.TestOrgID)
	return testhelpers.PerformPostRequest(
		uri,
		testhelpers.CurrentUserID,
		r,
		struct {
			Name string `json:"name"`
		}{studyName},
	)
}

var letterRunes = []rune("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")

func randStringRunes(n int) string {
	b := make([]rune, n)
	for i := range b {
		b[i] = letterRunes[rand.Intn(len(letterRunes))]
	}
	return string(b)
}
