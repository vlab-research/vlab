package testhelpers

import (
	"testing"

	types "github.com/vlab-research/vlab/api/internal/types"
)

type databasestudyconfoptions func(*types.DatabaseStudyConf)

func NewDatabaseStudyConf(opts ...databasestudyconfoptions) *types.DatabaseStudyConf {
	d := &types.DatabaseStudyConf{}
	// Set any Overrides
	for _, opt := range opts {
		opt(d)
	}
	return d

}

func TypeGeneral() databasestudyconfoptions {
	return func(d *types.DatabaseStudyConf) {
		d.StudyID = StudyID
		d.ConfType = "general"
		d.Conf = []byte(`{"name":"Foo","objective":"","optimization_goal":"link_clicks","destination_type":"Web","page_id":"1","min_budget":1.5,"opt_window":48,"instagram_id":"","ad_account":"12345"}`)
	}
}

func TypeRecruitment() databasestudyconfoptions {
	return func(d *types.DatabaseStudyConf) {
		d.StudyID = StudyID
		d.ConfType = "recruitment"
		d.Conf = []byte(`{"end_date":"2022-08-05T00:00:00","start_date":"2022-06-05T00:00:00","ad_campaign_name":"foobar-baz","budget":10000,"max_sample":1000}`)
	}
}

func TypeTargeting() databasestudyconfoptions {
	return func(d *types.DatabaseStudyConf) {
		d.StudyID = StudyID
		d.ConfType = "targeting"
		d.Conf = []byte(`{"template_campaign_name":"Bar","distribution_vars":"location"}`)
	}
}

func TypeTargetingDistribution() databasestudyconfoptions {
	return func(d *types.DatabaseStudyConf) {
		d.StudyID = StudyID
		d.ConfType = "targeting_distribution"
		d.Conf = []byte(`{"age":"21","gender":"F","location":"Spain"}`)
	}
}

func TypeDestinations() databasestudyconfoptions {
	return func(d *types.DatabaseStudyConf) {
		d.StudyID = StudyID
		d.ConfType = "destinations"
		d.Conf = []byte(`[{"type":"web","name":"typeform","url_template":"https://example.typeform.com/to/ABCDEF?ref={ref}"},{"type":"messenger","name":"fly","initial_shortcode":"foobarbaz"}]`)
	}
}

func TypeCreatives() databasestudyconfoptions {
	return func(d *types.DatabaseStudyConf) {
		d.StudyID = StudyID
		d.ConfType = "creatives"
		d.Conf = []byte(`[{"body":"Foobar","button_text":"Foobar","destination":"fly","image_hash":"8ef11493ade6deced04f36b9e8cf3900","link_text":"Foobar","name":"Ad1_Recruitment","welcome_message":"welcome","tags":null}]`)
	}
}

func TypeAudiences() databasestudyconfoptions {
	return func(d *types.DatabaseStudyConf) {
		d.StudyID = StudyID
		d.ConfType = "audiences"
		d.Conf = []byte(`[{"name":"Foobar","subtype":"LOOKALIKE","question_targeting":{"op":"not_equal","vars":[{"type":"variable","value":"hcw"},{"type":"constant","value":"E"}]}}]`)
	}
}

func TypeStrata() databasestudyconfoptions {
	return func(d *types.DatabaseStudyConf) {
		d.StudyID = StudyID
		d.ConfType = "strata"
		d.Conf = []byte(`[{"id":"foobar","quota":1,"audiences":["foobar"],"excluded_audiences":["bazqux"],"creatives":["foobar"],"facebook_targeting":{"age_max":65,"age_min":40,"genders":[2],"geo_locations":{"countries":["US"],"location_types":["home"]}},"question_targeting":{"op":"not_equal","vars":[{"type":"variable","value":"hcw"},{"type":"constant","value":"E"}]},"metadata":{"stratum_age":"40","stratum_gender":"2","stratum_location":"US"}}]`)
	}
}

func CreateDatabaseStudyConf(t *testing.T, dsc types.DatabaseStudyConf) error {
	t.Helper()
	r := GetRepositories()
	q := "INSERT INTO study_confs (study_id, conf_type, conf) VALUES ($1, $2, $3)"
	_, err := r.Db.Exec(q, dsc.StudyID, dsc.ConfType, dsc.Conf)
	return err
}
