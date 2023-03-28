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
func TestHandler_List(t *testing.T) {
	assert := require.New(t)
	type params struct {
		cursor string
		number string
	}
	testcases := []struct {
		studies        []types.Study
		params         params
		description    string
		expectedStatus int
		expectedRes    []string
	}{
		{
			description:    "return a 200 with the requested studies",
			expectedStatus: 200,
			studies: []types.Study{
				{
					ID:        "5372ca9c-9fcd-42d4-a596-d90792909917",
					Name:      "Example Study",
					Slug:      "example-study",
					CreatedAt: 1605049200000,
				},
			},
			params: params{
				cursor: "MA==",
				number: "10",
			},
			expectedRes: []string{`"id":"5372ca9c-9fcd-42d4-a596-d90792909917","name":"Example Study","slug":"example-study"`, `"pagination":{"nextCursor":null}}`},
		},
		{
			description:    "return a 200 with no studies",
			expectedStatus: 200,
			studies:        []types.Study{},
			params: params{
				cursor: "MA==",
				number: "10",
			},
			expectedRes: []string{`{"data":[],"pagination":{"nextCursor":null}}`},
		},
		{
			description:    "return a 400 with invalid cursor",
			expectedStatus: 400,
			studies:        []types.Study{},
			params: params{
				cursor: "not-valid",
				number: "10",
			},
			expectedRes: []string{`{"error":"Key: 'paginationQueryParams.CursorInBase64url' Error:Field validation for 'CursorInBase64url' failed on the 'base64url' tag"}`},
		},
		{
			description:    "return a 400 with invalid number",
			expectedStatus: 400,
			studies:        []types.Study{},
			params: params{
				cursor: "MA==",
				number: "101",
			},
			expectedRes: []string{`{"error":"Key: 'paginationQueryParams.Number' Error:Field validation for 'Number' failed on the 'lte' tag"}`},
		},
		{
			description:    "return a 200 with the requested studies",
			expectedStatus: 200,
			studies: []types.Study{
				{
					ID:        "5372ca9c-9fcd-42d4-a596-d90792909917",
					Name:      "Example Study",
					Slug:      "example-study",
					CreatedAt: 1605049200000,
				},
				{
					ID:        "94259273-d64c-4e1f-9a67-9b283d5d84b5",
					Name:      "Example Study2",
					Slug:      "example-study2",
					CreatedAt: 1605049200000,
				},
			},
			params: params{
				cursor: "MA==",
				number: "1",
			},
			expectedRes: []string{`"id":"5372ca9c-9fcd-42d4-a596-d90792909917","name":"Example Study","slug":"example-study"`, `"pagination":{"nextCursor":"MQ=="}`},
		},
	}

	for _, tc := range testcases {
		t.Run(fmt.Sprintf("should %s", tc.description),
			func(t *testing.T) {
				testhelpers.DeleteAllStudies(t)
				testhelpers.DeleteAllUsers(t)
				testhelpers.CreateUser(t)
				for _, study := range tc.studies {
					err := testhelpers.CreateStudyFromStudy(t, study)
					assert.NoError(err)
				}
				res := getStudiesRequest(t, tc.params.cursor, tc.params.number)
				assert.Equal(res.StatusCode, tc.expectedStatus)
				for _, expected := range tc.expectedRes {
					assert.Contains(res.Body, expected)
				}
			})
	}
}

func getStudiesRequest(t *testing.T, cursor, number string) testhelpers.Response {
	t.Helper()
	r := testhelpers.GetRepositories()
	r.User.Create(context.TODO(), testhelpers.CurrentUserID)
	return testhelpers.PerformGetRequest(
		fmt.Sprintf("/%s/studies?cursor=%s&number=%s", testhelpers.TestOrgID, cursor, number),
		r,
	)
}
