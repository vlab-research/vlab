package studyconfig_test

import (
	"context"
	"fmt"
	"testing"

	"github.com/stretchr/testify/require"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/storage"
	"github.com/vlab-research/vlab/dashboard-api/internal/testhelpers"
	"github.com/vlab-research/vlab/dashboard-api/internal/types"
)

func TestHandler_StudyConfiguration_Create(t *testing.T) {
	assert := require.New(t)
	userId := "auth0|61916c1dab79c900713936de"
	studyslug := "test-study"
	testcases := []struct {
		studyconfig    types.StudyConf
		studyslug      string
		description    string
		expectedStatus int
		expectedRes    string
	}{
		{
			studyconfig: types.StudyConf{
				UserID: userId,
				General: types.GeneralConf{
					Name:             "Foo",
					AdAccount:        "12345",
					DestinationType:  "Web",
					OptInWindow:      48,
					OptimizationGoal: "link_clicks",
					PageID:           "1",
					MinBudget:        1,
				},
				Targeting: types.TargetingConf{
					TemplateCampaignName: "Bar",
					DistributionVars:     types.Location,
				},
				TargetingDistribution: types.TargetingDistributionConf{
					Age:      "21",
					Gender:   "F",
					Location: "Spain",
				},
			},
			expectedStatus: 201,
			studyslug:      studyslug,
			expectedRes:    "{\"data\":{\"general\":{\"name\":\"Foo\",\"objective\":\"\",\"optimization_goal\":\"link_clicks\",\"destination_type\":\"Web\",\"page_id\":\"1\",\"min_budget\":1,\"opt_window\":48,\"instagram_id\":\"\",\"ad_account\":\"12345\"},\"targeting\":{\"template_campaign_name\":\"Bar\",\"distribution_vars\":\"location\"},\"targeting_distribution\":{\"age\":\"21\",\"gender\":\"F\",\"location\":\"Spain\"}}}",
			description:    "return 201 for valid studyconfig account",
		},
		{
			studyconfig: types.StudyConf{
				UserID: userId,
			},
			expectedStatus: 400,
			studyslug:      "",
			expectedRes:    "{\"error\":\"Key: 'Slug' Error:Field validation for 'Slug' failed on the 'required' tag\"}",
			description:    "return 400 with no slug",
		},
		{
			studyconfig: types.StudyConf{
				UserID: userId,
			},
			expectedStatus: 400,
			studyslug:      "invalid",
			expectedRes:    "{\"error\":\"failed finding study with identifier invalid\"}",
			description:    "return 400 with invalid slug",
		},
	}

	for _, tc := range testcases {
		t.Run(fmt.Sprintf("should  %s", tc.description),
			func(t *testing.T) {
				testhelpers.DeleteAllStudies()
				testhelpers.DeleteAllUsers()
				testhelpers.CreateUser()
				err := testhelpers.CreateStudy(studyslug, tc.studyconfig.UserID)
				res := createStudyConfRequest(tc.studyslug, tc.studyconfig)
				assert.NoError(err)
				assert.Contains(res.Body, tc.expectedRes)
				assert.Equal(res.StatusCode, tc.expectedStatus)
			})
	}

}

func createStudyConfRequest(slug string, sc types.StudyConf) testhelpers.Response {
	r := testhelpers.GetRepositories()
	r.User.CreateUser(context.TODO(), sc.UserID)
	return testhelpers.PerformPostRequest(
		fmt.Sprintf("/studies/%s/conf", slug),
		storage.Repositories{
			Study:     testhelpers.GetRepositories().Study,
			StudyConf: testhelpers.GetRepositories().StudyConf,
		},
		sc,
	)
}
