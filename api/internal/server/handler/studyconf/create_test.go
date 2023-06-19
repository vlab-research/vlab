package studyconf_test

import (
	"context"
	"fmt"
	"testing"

	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
	"github.com/vlab-research/vlab/api/internal/testhelpers"
)

func TestHandler_StudyConfiguration_Create(t *testing.T) {
	assert := require.New(t)
	id := uuid.New()
	studyslug := id.String()
	testcases := []struct {
		studyconfig    interface{}
		studyslug      string
		description    string
		expectedStatus int
		expectedRes    string
	}{
		{
			studyconfig:    testhelpers.NewStudyConf(),
			expectedStatus: 201,
			studyslug:      studyslug,
			expectedRes:    `{"data":{"general":{"name":"Foo","objective":"","optimization_goal":"link_clicks","destination_type":"Web","page_id":"1","min_budget":1.5,"opt_window":48,"instagram_id":"","ad_account":"12345"},"targeting":{"template_campaign_name":"Bar","distribution_vars":"location"},"targeting_distribution":{"age":"21","gender":"F","location":"Spain"},"recruitment":{"end_date":"2022-08-05T00:00:00","start_date":"2022-06-05T00:00:00","ad_campaign_name":"foobar-baz","budget":10000,"max_sample":1000},"destinations":[{"type":"web","name":"typeform","url_template":"https://example.typeform.com/to/ABCDEF?ref={ref}"},{"type":"messenger","name":"fly","initial_shortcode":"foobarbaz"}],"creatives":[{"body":"Foobar","button_text":"Foobar","destination":"fly","image_hash":"8ef11493ade6deced04f36b9e8cf3900","link_text":"Foobar","name":"Ad1_Recruitment","welcome_message":"welcome","tags":null}],"audiences":[{"name":"Foobar","subtype":"LOOKALIKE","question_targeting":{"op":"not_equal","vars":[{"type":"variable","value":"hcw"},{"type":"constant","value":"E"}]}}],"strata":[{"id":"foobar","quota":1,"audiences":["foobar"],"excluded_audiences":["bazqux"],"creatives":["foobar"],"facebook_targeting":{"age_max":65,"age_min":40,"genders":[2],"geo_locations":{"countries":["US"],"location_types":["home"]}},"question_targeting":{"op":"not_equal","vars":[{"type":"variable","value":"hcw"},{"type":"constant","value":"E"}]},"metadata":{"stratum_age":"40","stratum_gender":"2","stratum_location":"US"}}]}}`,
			description:    "return 201 for valid studyconfig",
		},
		{
			studyconfig:    `{"data":{"destinations":[{"name": "app test", "app_install_link": "some link", "app_install_state": "some state", "deeplink_template": "template", "facebook_app_id": "id fb", "user_device": ["device 1", "device 2"], "user_os": "user os 1"}]}}`,
			expectedStatus: 400,
			studyslug:      studyslug,
			expectedRes:    `{"error":"json: cannot unmarshal string into Go value of type types.StudyConf"}`,
			description:    "return 400 for invalid destination structure",
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
		t.Run(fmt.Sprintf("should %s", tc.description),
			func(t *testing.T) {
				testhelpers.DeleteAllStudies(t)
				testhelpers.DeleteAllUsers(t)
				testhelpers.CreateUser(t)
				err := testhelpers.CreateStudy(t, studyslug, testhelpers.CurrentUserID)
				res := createStudyConfRequest(t, tc.studyslug, tc.studyconfig)
				assert.NoError(err)
				assert.Equal(tc.expectedRes, res.Body)
				assert.Equal(res.StatusCode, tc.expectedStatus)
			})
	}

}

func createStudyConfRequest(t *testing.T, slug string, sc interface{}) testhelpers.Response {
	t.Helper()
	r := testhelpers.GetRepositories()
	uri := fmt.Sprintf("/%s/studies/%s/conf", testhelpers.TestOrgID, slug)
	r.User.Create(context.TODO(), testhelpers.CurrentUserID)
	return testhelpers.PerformPostRequest(uri, testhelpers.CurrentUserID, r, sc)
}
