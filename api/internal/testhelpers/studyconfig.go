package testhelpers

import (
	"testing"

	types "github.com/vlab-research/vlab/api/internal/types"
)

const StudyID = "92b322df-9dac-4240-a88e-d3aa715be83d"

type studyconfigoptions func(*types.StudyConf)

// NewStudyConf is a test helper that generates a studyconf with some sensible
// defaults and allows for overrides, please make use of this in tests as this
// structure might change and it will be easier to update this in a single
// place.
//
// example: return full studyConfig
//
// sc := NewStudyConf()
//
// example: set one of the confs to nil
//
// sc := NewStudyConf(WithTargetingConf(nil))
//
// example: override one of the confs (you need to pass in all fields of
// specified conf)
//
// general := &types.GeneralConf{ Name: "bar", etc...}
//
// sc := NewStudyConf(WithGeneralConf(general))
func NewStudyConf(opts ...studyconfigoptions) types.StudyConf {

	// This is used to mock out the questioning target
	// which has a recursive structure that is difficult to reproduce
	// we need to have a type of []interface{}
	// however you can not do a composite literal (inline initialize)
	// with these values
	vars := make([]interface{}, 0)
	vars = append(vars, map[string]interface{}{
		"type":  "variable",
		"value": "hcw",
	})
	vars = append(vars, map[string]interface{}{
		"type":  "constant",
		"value": "E",
	})

	// This is where we set the defaults for tests
	sc := &types.StudyConf{
		StudyID: StudyID,
		UserID:  CurrentUserID,
		General: &types.GeneralConf{
			Name:             "Foo",
			AdAccount:        "12345",
			DestinationType:  "Web",
			OptInWindow:      48,
			OptimizationGoal: "link_clicks",
			PageID:           "1",
			MinBudget:        1.5,
		},
		Recruitment: &types.RecruitmentConf{
			AdCampaignName: "foobar-baz",
			Budget:         10000,
			EndDate:        "2022-08-05T00:00:00",
			StartDate:      "2022-06-05T00:00:00",
			MaxSample:      1000,
		},
		Destinations: &types.DestinationConf{
			&types.WebDestination{
				Type:        "web",
				Name:        "typeform",
				URLTemplate: "https://example.typeform.com/to/ABCDEF?ref={ref}",
			},
			&types.FlyDestination{
				Type:             "messenger",
				Name:             "fly",
				InitialShortcode: "foobarbaz",
			},
		},
		Creatives: []*types.CreativeConf{
			{
				Body:           "Foobar",
				ButtonText:     "Foobar",
				Destination:    "fly",
				ImageHash:      "8ef11493ade6deced04f36b9e8cf3900",
				LinkText:       "Foobar",
				Name:           "Ad1_Recruitment",
				WelcomeMessage: "welcome",
			},
		},
		Variables: []*types.VariableConf{
			{
				Name:       "age",
				Properties: []string{"age_min", "age_max"},
				Levels: []*types.Level{
					{
						Name:             "18",
						TemplateCampaign: "template",
						TemplateAdset:    "18",
						FacebookTargeting: &types.FacebookTargeting{
							"genders": []interface{}{float64(2)},
						},
						Quota: 0.5,
					},
				},
			},
		},
		Strata: []*types.StratumConf{
			{
				ID:                "foobar",
				Quota:             1.0,
				Audiences:         []string{"foobar"},
				Creatives:         []string{"foobar"},
				ExcludedAudiences: []string{"bazqux"},
				FacebookTargeting: &types.FacebookTargeting{
					"age_max": float64(65),
					"age_min": float64(40),
					"genders": []interface{}{float64(2)},
					"geo_locations": map[string]interface{}{
						"countries":      []interface{}{"US"},
						"location_types": []interface{}{"home"},
					},
				},
				Metadata: &types.Metadata{
					"stratum_age":      "40",
					"stratum_gender":   "2",
					"stratum_location": "US",
				},
				QuestionTargeting: &types.QuestionTargeting{
					"op":   "not_equal",
					"vars": vars,
				},
			},
		},
		Audiences: []*types.AudienceConf{
			{
				Name:    "Foobar",
				SubType: "LOOKALIKE",
				QuestionTargeting: &types.QuestionTargeting{
					"op":   "not_equal",
					"vars": vars,
				},
			},
		},
	}

	// Set any Overrides
	for _, opt := range opts {
		opt(sc)
	}
	return *sc
}

// WithGeneralConf is used to override the default GeneralConf
func WithGeneralConf(g *types.GeneralConf) studyconfigoptions {
	return func(sc *types.StudyConf) {
		sc.General = g
	}
}

// WithRecruitmentConf is used to override the default RecruitmentConf
func WithRecruitmentConf(r *types.RecruitmentConf) studyconfigoptions {
	return func(sc *types.StudyConf) {
		sc.Recruitment = r
	}
}

// WithStratumConf is used to override the default StrataConf
func WithStratumConf(s []*types.StratumConf) studyconfigoptions {
	return func(sc *types.StudyConf) {
		sc.Strata = s
	}
}

// WithDestinationConf is used to override the default DestinationConf
func WithDestinationConf(d *types.DestinationConf) studyconfigoptions {
	return func(sc *types.StudyConf) {
		sc.Destinations = d
	}
}

// WithAudiences is used to override the default AudienceConf
func WithAudiences(as []*types.AudienceConf) studyconfigoptions {
	return func(sc *types.StudyConf) {
		sc.Audiences = as
	}
}

func WithVariables(as []*types.VariableConf) studyconfigoptions {
	return func(sc *types.StudyConf) {
		sc.Variables = as
	}
}

// DeleteAllStudyConfs Helper function that clears the study_confs table
func DeleteAllStudyConfs(t *testing.T) {
	t.Helper()
	repositories := GetRepositories()
	repositories.Db.Exec("DELETE FROM study_conf")
}
