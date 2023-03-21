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
				{
					StudyID:  studyslug,
					ConfType: "general",
					Conf:     []byte(`{"name":"Foo","objective":"","optimization_goal":"link_clicks","destination_type":"Web","page_id":"1","min_budget":1,"opt_window":48,"instagram_id":"","ad_account":"12345"}`),
				},
			},
			expectedStatus: 200,
			studyslug:      studyslug,
			expectedRes:    "{\"data\":{\"general\":{\"name\":\"Foo\",\"objective\":\"\",\"optimization_goal\":\"link_clicks\",\"destination_type\":\"Web\",\"page_id\":\"1\",\"min_budget\":1,\"opt_window\":48,\"instagram_id\":\"\",\"ad_account\":\"12345\"},\"targeting\":null,\"targeting_distribution\":null}}",
			description:    "return 200 for valid studyconfig account",
		},
	}

	for _, tc := range testcases {
		t.Run(fmt.Sprintf("should %s", tc.description),
			func(t *testing.T) {
				testhelpers.DeleteAllStudies()
				testhelpers.DeleteAllUsers()
				testhelpers.CreateUser()
				err := testhelpers.CreateStudy(studyslug, testhelpers.CurrentUserId)
				assert.NoError(err)
				for _, dsc := range tc.databasestudyconfs {
					err := testhelpers.CreateDatabaseStudyConf(*dsc)
					assert.NoError(err)
				}
				res := getStudyConfRequest(tc.studyslug)
				assert.Contains(res.Body, tc.expectedRes)
				assert.Equal(res.StatusCode, tc.expectedStatus)
			})
	}

}

func getStudyConfRequest(slug string) testhelpers.Response {
	r := testhelpers.GetRepositories()
	r.User.CreateUser(context.TODO(), testhelpers.CurrentUserId)
	return testhelpers.PerformGetRequest(
		fmt.Sprintf("/studies/%s/conf", slug),
		storage.Repositories{
			Study:     testhelpers.GetRepositories().Study,
			StudyConf: testhelpers.GetRepositories().StudyConf,
		},
	)
}
