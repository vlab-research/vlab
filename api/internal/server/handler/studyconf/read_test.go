package studyconf_test

import (
	"context"
	"fmt"
	"testing"

	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
	"github.com/vlab-research/vlab/api/internal/testhelpers"
	"github.com/vlab-research/vlab/api/internal/types"
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
			expectedRes:    `{"data":{"general":{"name":"Foo","objective":"","optimization_goal":"link_clicks","destination_type":"Web","page_id":"1","min_budget":1.5,"opt_window":48,"instagram_id":"","ad_account":"12345"},"recruitment":null,"destinations":null,"creatives":null,"audiences":null,"variables":null,"strata":null}}`,
			description:    "return 200 for valid studyconfig with only general",
		},
		{
			databasestudyconfs: []*types.DatabaseStudyConf{
				testhelpers.NewDatabaseStudyConf(testhelpers.TypeGeneral()),
				testhelpers.NewDatabaseStudyConf(testhelpers.TypeRecruitment()),
				testhelpers.NewDatabaseStudyConf(testhelpers.TypeDestinations()),
				testhelpers.NewDatabaseStudyConf(testhelpers.TypeCreatives()),
				testhelpers.NewDatabaseStudyConf(testhelpers.TypeAudiences()),
				testhelpers.NewDatabaseStudyConf(testhelpers.TypeVariables()),
				testhelpers.NewDatabaseStudyConf(testhelpers.TypeStrata()),
			},
			expectedStatus: 200,
			studyslug:      studyslug,
			description:    "return 200 for valid studyconfig with all config",
			expectedRes:    `{"data":{"general":{"name":"Foo","objective":"","optimization_goal":"link_clicks","destination_type":"Web","page_id":"1","min_budget":1.5,"opt_window":48,"instagram_id":"","ad_account":"12345"},"recruitment":{"end_date":"2022-08-05T00:00:00","start_date":"2022-06-05T00:00:00","ad_campaign_name":"foobar-baz","budget":10000,"max_sample":1000},"destinations":[{"type":"web","name":"typeform","url_template":"https://example.typeform.com/to/ABCDEF?ref={ref}"},{"type":"messenger","name":"fly","initial_shortcode":"foobarbaz"}],"creatives":[{"body":"Foobar","button_text":"Foobar","destination":"fly","image_hash":"8ef11493ade6deced04f36b9e8cf3900","link_text":"Foobar","name":"Ad1_Recruitment","welcome_message":"welcome","tags":null}],"audiences":[{"name":"Foobar","subtype":"LOOKALIKE","question_targeting":{"op":"not_equal","vars":[{"type":"variable","value":"hcw"},{"type":"constant","value":"E"}]}}],"variables":[{"name":"age","properties":["age_min","age_max"],"levels":[{"name":"18","template_campaign":"template","template_adset":"18","facebook_targeting":{"genders":[2]},"quota":0.5}]}],"strata":[{"id":"foobar","quota":1,"audiences":["foobar"],"excluded_audiences":["bazqux"],"creatives":["foobar"],"facebook_targeting":{"age_max":65,"age_min":40,"genders":[2],"geo_locations":{"countries":["US"],"location_types":["home"]}},"question_targeting":{"op":"not_equal","vars":[{"type":"variable","value":"hcw"},{"type":"constant","value":"E"}]},"metadata":{"stratum_age":"40","stratum_gender":"2","stratum_location":"US"}}]}}`,
		},
		{
			databasestudyconfs: []*types.DatabaseStudyConf{
				{
					StudyID:  testhelpers.StudyID,
					ConfType: "general",
					Conf:     []byte(`[{"name":"Foo","objective":"","optimization_goal":"link_clicks","destination_type":"Web","page_id":"1","min_budget":1.5,"opt_window":48,"instagram_id":"","ad_account":"12345"}]`),
				},
			},
			expectedStatus: 400,
			studyslug:      studyslug,
			expectedRes:    `{"error":"an unexpected error occured - there was an error fetching the general configuration"}`,
			description:    "return 400 for invalid studyconfig in database",
		},
	}

	for _, tc := range testcases {
		t.Run(fmt.Sprintf("should %s", tc.description),
			func(t *testing.T) {
				testhelpers.DeleteAllStudies(t)
				testhelpers.DeleteAllStudyConfs(t)
				testhelpers.DeleteAllUsers(t)
				testhelpers.CreateUser(t)
				err := testhelpers.CreateStudy(t, studyslug, testhelpers.CurrentUserID)
				assert.NoError(err)
				for _, dsc := range tc.databasestudyconfs {
					err := testhelpers.CreateDatabaseStudyConf(t, *dsc)
					assert.NoError(err)
				}
				res := getStudyConfRequest(t, tc.studyslug)
				assert.Equal(tc.expectedRes, res.Body)
				assert.Equal(res.StatusCode, tc.expectedStatus)
			})
	}

}

func getStudyConfRequest(t *testing.T, slug string) testhelpers.Response {
	t.Helper()
	r := testhelpers.GetRepositories()
	r.User.Create(context.TODO(), testhelpers.CurrentUserID)
	uri := fmt.Sprintf("/%s/studies/%s/conf", testhelpers.TestOrgID, slug)
	return testhelpers.PerformGetRequest(uri, r)
}
