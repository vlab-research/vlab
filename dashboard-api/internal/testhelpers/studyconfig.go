package testhelpers

import (
	"testing"

	types "github.com/vlab-research/vlab/dashboard-api/internal/types"
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

	// This is where we set the defaults for tests
	sc := &types.StudyConf{
		StudyID: StudyID,
		UserID:  CurrentUserId,
		General: &types.GeneralConf{
			Name:             "Foo",
			AdAccount:        "12345",
			DestinationType:  "Web",
			OptInWindow:      48,
			OptimizationGoal: "link_clicks",
			PageID:           "1",
			MinBudget:        1,
		},
		Targeting: &types.TargetingConf{
			TemplateCampaignName: "Bar",
			DistributionVars:     types.Location,
		},
		TargetingDistribution: &types.TargetingDistributionConf{
			Age:      "21",
			Gender:   "F",
			Location: "Spain",
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
				Name:        "typeform",
				URLTemplate: "https://example.typeform.com/to/ABCDEF?ref={ref}",
			},
			&types.FlyDestination{
				Name:             "fly",
				InitialShortcode: "foobarbaz",
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

// WithDestinationConf is used to override the default DestinationConf
func WithDestinationConf(d *types.DestinationConf) studyconfigoptions {
	return func(sc *types.StudyConf) {
		sc.Destinations = d
	}
}

// WithTargetingConf is used to overide the default TargetingConf
func WithTargetingConf(t *types.TargetingConf) studyconfigoptions {
	return func(sc *types.StudyConf) {
		sc.Targeting = t
	}
}

// WithTargetingDistributionConf is used to override the default TargetingDistributionConf
func WithTargetingDistributionConf(
	t *types.TargetingDistributionConf,
) studyconfigoptions {
	return func(sc *types.StudyConf) {
		sc.TargetingDistribution = t
	}
}

// DeleteAllStudyConfs Helper function that clears the study_confs table
func DeleteAllStudyConfs(t *testing.T) {
	t.Helper()
	repositories := GetRepositories()
	repositories.Db.Exec("DELETE FROM study_conf")
}
