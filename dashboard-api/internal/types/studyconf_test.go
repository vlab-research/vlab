package types

import (
	"fmt"
	"testing"

	"github.com/stretchr/testify/require"
)

func TestStudyConfType(t *testing.T) {
	assert := require.New(t)
	t.Run("can transform an entire studyconf for database", func(t *testing.T) {
		input := StudyConf{
			StudyID: "foobar",
			UserID:  "baz",
			General: GeneralConf{
				Name:             "Foo",
				AdAccount:        "12345",
				DestinationType:  "Web",
				OptInWindow:      48,
				OptimizationGoal: "link_clicks",
				PageID:           "1",
				MinBudget:        1,
			},
			Targeting: TargetingConf{
				TemplateCampaignName: "Bar",
				DistributionVars:     Location,
			},
			TargetingDistribution: TargetingDistributionConf{
				Age:      "21",
				Gender:   "F",
				Location: "Spain",
			},
		}
		expected := []DatabaseStudyConf{
			{
				StudyID:  "foobar",
				ConfType: "general",
				Conf:     []byte(`{"name":"Foo","objective":"","optimization_goal":"link_clicks","destination_type":"Web","page_id":"1","min_budget":1,"opt_window":48,"instagram_id":"","ad_account":"12345"}`),
			},
			{
				StudyID:  "foobar",
				ConfType: "targeting",
				Conf:     []byte(`{"template_campaign_name":"Bar","distribution_vars":"location"}`),
			},
			{
				StudyID:  "foobar",
				ConfType: "targeting_distribution",
				Conf:     []byte(`{"age":"21","gender":"F","location":"Spain"}`),
			},
		}
		s, err := input.TransformForDatabase()
		assert.NoError(err)
		for i, _ := range expected {
			fmt.Printf("%s\n%s\n", expected[i], s[i].Conf)
			assert.Equal(expected[i], s[i])
		}
	})
	t.Run("does not transform null confs", func(t *testing.T) {
		input := StudyConf{
			StudyID: "foobar",
			UserID:  "baz",
			General: GeneralConf{
				Name:             "Foo",
				AdAccount:        "12345",
				DestinationType:  "Web",
				OptInWindow:      48,
				OptimizationGoal: "link_clicks",
				PageID:           "1",
				MinBudget:        1,
			},
			Targeting: TargetingConf{
				TemplateCampaignName: "Bar",
				DistributionVars:     Location,
			},
		}
		expected := []DatabaseStudyConf{
			{
				StudyID:  "foobar",
				ConfType: "general",
				Conf:     []byte(`{"name":"Foo","objective":"","optimization_goal":"link_clicks","destination_type":"Web","page_id":"1","min_budget":1,"opt_window":48,"instagram_id":"","ad_account":"12345"}`),
			},
			{
				StudyID:  "foobar",
				ConfType: "targeting",
				Conf:     []byte(`{"template_campaign_name":"Bar","distribution_vars":"location"}`),
			},
		}
		s, err := input.TransformForDatabase()
		assert.NoError(err)
		assert.Equal(len(s), 2)
		for i, _ := range expected {
			assert.Equal(expected[i], s[i])
		}
	})
}
