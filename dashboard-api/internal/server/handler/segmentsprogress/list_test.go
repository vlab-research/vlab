package segmentsprogress_test

import (
	"context"
	"fmt"
	"testing"

	"github.com/stretchr/testify/require"
	studiesmanager "github.com/vlab-research/vlab/dashboard-api/internal"
	"github.com/vlab-research/vlab/dashboard-api/internal/testhelpers"
)

func TestHandler_List(t *testing.T) {

	testcases := []struct {
		segmentsprogress []studiesmanager.SegmentsProgress
		studyslug        string
		description      string
		expectedStatus   int
		expectedRes      string
	}{
		{
			description:    "200 with all time segments progress for the specified study",
			expectedStatus: 200,
			studyslug:      testhelpers.StudySlug,
			expectedRes:    `{"data":[{"segments":[{"id":"25-spain-male","name":"25-spain-male","datetime":1605045600000000,"currentBudget":72000,"desiredPercentage":5,"currentPercentage":0,"expectedPercentage":0,"desiredParticipants":null,"expectedParticipants":0,"currentParticipants":0,"currentPricePerParticipant":0,"percentageDeviationFromGoal":5}],"datetime":1605045600000000}]}`,
			segmentsprogress: []studiesmanager.SegmentsProgress{
				{
					Segments: []studiesmanager.SegmentProgress{
						{
							ID:                          "25-spain-male",
							Name:                        "25-spain-male",
							Datetime:                    1605045600000,
							CurrentBudget:               72000,
							DesiredPercentage:           5,
							CurrentPercentage:           0,
							ExpectedPercentage:          0,
							DesiredParticipants:         (*int64)(nil),
							ExpectedParticipants:        0,
							CurrentParticipants:         0,
							CurrentPricePerParticipant:  0,
							PercentageDeviationFromGoal: 5,
						},
					},
					Datetime: 1605045600000,
				},
			},
		},
		{
			description:      "200 with empty data when no segments found",
			expectedStatus:   200,
			studyslug:        testhelpers.StudySlug,
			expectedRes:      `{"data":[]}`,
			segmentsprogress: []studiesmanager.SegmentsProgress{},
		},
	}

	for _, tc := range testcases {
		assert := require.New(t)
		t.Run(fmt.Sprintf("should %s", tc.description), func(t *testing.T) {
			testhelpers.DeleteAllStudies(t)
			testhelpers.DeleteAllUsers(t)
			testhelpers.DeleteAllStudySegments(t)
			testhelpers.CreateUser(t)
			err := testhelpers.CreateStudy(t, testhelpers.StudySlug, testhelpers.CurrentUserId)
			assert.NoError(err)
			err = testhelpers.CreateSegment(t, tc.segmentsprogress)
			assert.NoError(err)
			res := getStudySegmentRequest(t, tc.studyslug)
			assert.Equal(tc.expectedRes, res.Body)
			assert.Equal(res.StatusCode, tc.expectedStatus)
		})
	}

}

func getStudySegmentRequest(t *testing.T, slug string) testhelpers.Response {
	t.Helper()
	r := testhelpers.GetRepositories()
	r.User.CreateUser(context.TODO(), testhelpers.CurrentUserId)
	return testhelpers.PerformGetRequest(
		fmt.Sprintf("/studies/%s/segments-progress", slug),
		testhelpers.GetRepositories(),
	)
}
