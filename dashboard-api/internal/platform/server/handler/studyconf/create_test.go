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

func TestHandler_StudyConfiguration_Create(t *testing.T) {
	assert := require.New(t)
	id := uuid.New()
	studyslug := id.String()
	testcases := []struct {
		studyconfig    types.StudyConf
		studyslug      string
		description    string
		expectedStatus int
		expectedRes    string
	}{
		{
			studyconfig:    testhelpers.NewStudyConf(),
			expectedStatus: 201,
			studyslug:      studyslug,
			expectedRes:    `{"data":{"general":{"name":"Foo","objective":"","optimization_goal":"link_clicks","destination_type":"Web","page_id":"1","min_budget":1,"opt_window":48,"instagram_id":"","ad_account":"12345"},"targeting":{"template_campaign_name":"Bar","distribution_vars":"location"},"targeting_distribution":{"age":"21","gender":"F","location":"Spain"},"recruitment":{"end_date":"2022-08-05T00:00:00","start_date":"2022-06-05T00:00:00","ad_campaign_name":"foobar-baz","budget":10000,"max_sample":1000},"destinations":[{"name":"typeform","url_template":"https://example.typeform.com/to/ABCDEF?ref={ref}"},{"name":"fly","initial_shortcode":"foobarbaz"}],"creatives":[{"body":"Foobar","button_text":"Foobar","destination":"fly","image_hash":"8ef11493ade6deced04f36b9e8cf3900","link_text":"Foobar","name":"Ad1_Recruitment","welcome_message":"welcome","tags":null}]}}`,
			description:    "return 201 for valid studyconfig",
		},
		{
			studyconfig: testhelpers.NewStudyConf(
				testhelpers.WithGeneralConf(nil),
				testhelpers.WithRecruitmentConf(nil),
				testhelpers.WithTargetingConf(nil),
				testhelpers.WithTargetingDistributionConf(nil),
			),
			expectedStatus: 400,
			studyslug:      "",
			expectedRes:    `{"error":"Key: 'Slug' Error:Field validation for 'Slug' failed on the 'required' tag"}`,
			description:    "return 400 with no slug",
		},
		{
			studyconfig: testhelpers.NewStudyConf(
				testhelpers.WithGeneralConf(nil),
				testhelpers.WithRecruitmentConf(nil),
				testhelpers.WithTargetingConf(nil),
				testhelpers.WithTargetingDistributionConf(nil),
			),
			expectedStatus: 400,
			studyslug:      "invalid",
			expectedRes:    `{"error":"failed finding study with identifier invalid"}`,
			description:    "return 400 with invalid slug",
		},
	}

	for _, tc := range testcases {
		t.Run(fmt.Sprintf("should  %s", tc.description),
			func(t *testing.T) {
				testhelpers.DeleteAllStudies(t)
				testhelpers.DeleteAllUsers(t)
				testhelpers.CreateUser(t)
				err := testhelpers.CreateStudy(t, studyslug, tc.studyconfig.UserID)
				res := createStudyConfRequest(t, tc.studyslug, tc.studyconfig)
				assert.NoError(err)
				assert.Equal(tc.expectedRes, res.Body)
				assert.Equal(res.StatusCode, tc.expectedStatus)
			})
	}

}

func createStudyConfRequest(t *testing.T, slug string, sc types.StudyConf) testhelpers.Response {
	t.Helper()
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
