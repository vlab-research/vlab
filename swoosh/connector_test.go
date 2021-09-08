package main

import (
	"context"
	"encoding/json"
	"testing"

	"github.com/jackc/pgx/v4/pgxpool"
	"github.com/stretchr/testify/assert"
)

const (
	studiesSql = `
        drop table if exists studies;
        create table studies(
              id UUID default gen_random_uuid(),
              name string,
              active bool
        );
        `
	studyConfsSql = `
        drop table if exists study_confs;
        create table study_confs(
              created timestamp default current_timestamp(),
              study_id UUID,
              conf_type string,
              conf JSON
        );
        `

	confA = `
	[{
	    "source": "literacy_data_api",
	    "config": {
		"from": "0",
		"app_id": "appid",
		"attribution_id": "attribution"
	    }
	}]
       `
	confB = `
	[{
	    "source": "literacy_data_api",
	    "config": {
		"from": "0",
		"app_id": "appid",
		"attribution_id": "attribution"
	    }
	},
        {
	    "source": "another_source",
	    "config": {}
	}]
       `

	confC = `
	[{
	    "source": "literacy_data_api",
	    "config": {
		"from": "0",
		"app_id": "appid",
		"attribution_id": "attribution_later"
	    }
	}]
       `

	insertStudy = `insert into studies(name, active) values($1, $2) returning id`
	insertConf  = `insert into study_confs(study_id, conf_type, conf) values($1, $2, $3)`
)

func createStudy(pool *pgxpool.Pool, name string, active bool) string {
	var id string
	pool.QueryRow(context.Background(), insertStudy, name, active).Scan(&id)
	return id
}

func parseParams(d json.RawMessage) *LitDataAPIParams {
	params := new(LitDataAPIParams)
	err := json.Unmarshal(d, params)
	handle(err)
	return params
}

func TestGetStudyConfs_GetsOnlyActiveStudies(t *testing.T) {
	pool := testPool()
	defer pool.Close()
	mustExec(t, pool, studiesSql)
	mustExec(t, pool, studyConfsSql)

	foo := createStudy(pool, "foo", true)
	bar := createStudy(pool, "bar", false)

	mustExec(t, pool, insertConf, foo, "data_source", confA)
	mustExec(t, pool, insertConf, bar, "data_source", confA)

	confs, err := GetStudyConfs(pool, "literacy_data_api")

	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs))
}

func TestGetStudyConfs_GetsOnlyStudiesWithCorrectSource(t *testing.T) {
	pool := testPool()
	defer pool.Close()
	mustExec(t, pool, studiesSql)
	mustExec(t, pool, studyConfsSql)

	foo := createStudy(pool, "foo", true)

	mustExec(t, pool, insertConf, foo, "data_source", confB)

	confs, err := GetStudyConfs(pool, "literacy_data_api")

	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs))

	params := parseParams(confs[0].Conf.Config)
	assert.Equal(t, "attribution", params.AttributionID)
}

func TestGetStudyConfs_GetsOnlyTheLatestConfPerStudy(t *testing.T) {
	pool := testPool()
	defer pool.Close()
	mustExec(t, pool, studiesSql)
	mustExec(t, pool, studyConfsSql)

	foo := createStudy(pool, "foo", true)

	mustExec(t, pool, insertConf, foo, "data_source", confA)
	mustExec(t, pool, insertConf, foo, "data_source", confC)

	confs, err := GetStudyConfs(pool, "literacy_data_api")

	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs))
	params := parseParams(confs[0].Conf.Config)
	assert.Equal(t, "attribution_later", params.AttributionID)
}
