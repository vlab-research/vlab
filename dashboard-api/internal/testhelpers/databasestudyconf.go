package testhelpers

import (
	"testing"

	types "github.com/vlab-research/vlab/dashboard-api/internal/types"
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
		d.Conf = []byte(`{"name":"Foo","objective":"","optimization_goal":"link_clicks","destination_type":"Web","page_id":"1","min_budget":1,"opt_window":48,"instagram_id":"","ad_account":"12345"}`)
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

func CreateDatabaseStudyConf(t *testing.T, dsc types.DatabaseStudyConf) error {
	t.Helper()
	r := GetRepositories()
	q := "INSERT INTO study_confs (study_id, conf_type, conf) VALUES ($1, $2, $3)"
	_, err := r.Db.Exec(q, dsc.StudyID, dsc.ConfType, dsc.Conf)
	return err
}
