package studyconf_test

import (
	"context"
	"fmt"
	"testing"

	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/storage"
	"github.com/vlab-research/vlab/dashboard-api/internal/testhelpers"
	"github.com/vlab-research/vlab/dashboard-api/internal/types"
)

func TestHandler_StudyConfiguration_GetByStudySlug(t *testing.T) {
	assert := require.New(t)
	id := uuid.New()
	studyslug := id.String()
	testcases := []struct {
		databasestudyconfs []*types.DatabaseStudyConf
		studyslug          string
		description        string
		expectedStatus     int
		expectedRes        string
	}{
		{
			databasestudyconfs: []*types.DatabaseStudyConf{
				testhelpers.NewDatabaseStudyConf(testhelpers.TypeGeneral()),
			},
			expectedStatus: 200,
			studyslug:      studyslug,
			expectedRes:    `{"data":{"general":{"name":"Foo","objective":"","optimization_goal":"link_clicks","destination_type":"Web","page_id":"1","min_budget":1,"opt_window":48,"instagram_id":"","ad_account":"12345"},"targeting":null,"targeting_distribution":null,"recruitment":null}}`,
			description:    "return 200 for valid studyconfig account with only general",
		},
		{
			databasestudyconfs: []*types.DatabaseStudyConf{
				testhelpers.NewDatabaseStudyConf(testhelpers.TypeGeneral()),
				testhelpers.NewDatabaseStudyConf(testhelpers.TypeRecruitment()),
			},
			expectedStatus: 200,
			studyslug:      studyslug,
			expectedRes:    `{"data":{"general":{"name":"Foo","objective":"","optimization_goal":"link_clicks","destination_type":"Web","page_id":"1","min_budget":1,"opt_window":48,"instagram_id":"","ad_account":"12345"},"targeting":null,"targeting_distribution":null,"recruitment":{"end_date":"2022-08-05T00:00:00","start_date":"2022-06-05T00:00:00","ad_campaign_name":"foobar-baz","budget":10000,"max_sample":1000}}}`,
			description:    "return 200 for valid studyconfig account with general and recruitment",
		},
	}

	for _, tc := range testcases {
		t.Run(fmt.Sprintf("should %s", tc.description),
			func(t *testing.T) {
				testhelpers.DeleteAllStudies(t)
				testhelpers.DeleteAllStudyConfs(t)
				testhelpers.DeleteAllUsers(t)
				testhelpers.CreateUser(t)
				err := testhelpers.CreateStudy(t, studyslug, testhelpers.CurrentUserId)
				assert.NoError(err)
				for _, dsc := range tc.databasestudyconfs {
					err := testhelpers.CreateDatabaseStudyConf(t, *dsc)
					assert.NoError(err)
				}
				res := getStudyConfRequest(t, tc.studyslug)
				assert.Equal(res.Body, tc.expectedRes)
				assert.Equal(res.StatusCode, tc.expectedStatus)
			})
	}

}

func getStudyConfRequest(t *testing.T, slug string) testhelpers.Response {
	t.Helper()
	r := testhelpers.GetRepositories()
	r.User.CreateUser(context.TODO(), testhelpers.CurrentUserId)
	return testhelpers.PerformGetRequest(
		fmt.Sprintf("/studies/%s/conf", slug),
		storage.Repositories{
			StudyConf: testhelpers.GetRepositories().StudyConf,
		},
	)
}
