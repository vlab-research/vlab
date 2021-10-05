package main

import (
	"context"
	"encoding/json"
	"fmt"
	"testing"
	"time"

	"github.com/jackc/pgx/v4/pgxpool"
	"github.com/stretchr/testify/assert"
)

const (
	confA = `
	[{
            "name": "A1",
	    "source": "literacy_data_api",
	    "config": {
		"from": 0,
		"app_id": "appid",
		"attribution_id": "attribution"
	    }
	}]
       `
	confB = `
	[{
            "name": "B1",
	    "source": "literacy_data_api",
	    "config": {
		"from": 0,
		"app_id": "appid",
		"attribution_id": "attribution"
	    }
	},
        {
            "name": "B2",
	    "source": "another_source",
	    "config": {}
	}]
       `

	confC = `
	[{
            "name": "C1",
	    "source": "literacy_data_api",
	    "config": {
		"from": 0,
		"app_id": "appid",
		"attribution_id": "attribution_later"
	    }
	}]
       `

	confD = `
	[{
            "name": "D1",
	    "source": "literacy_data_api",
	    "config": {
		"from": 0,
		"app_id": "appid",
		"attribution_id": "attribution"
	    }
	},
        {
            "name": "D2",
	    "source": "literacy_data_api",
	    "config": {
		"from": 0,
		"app_id": "appid2",
		"attribution_id": "attribution2"
	    }
	}]
       `

	insertStudy = `insert into studies(name, active) values($1, $2) returning id`
	insertConf  = `insert into study_confs(study_id, conf_type, conf) values($1, $2, $3)`
)

func resetDb(pool *pgxpool.Pool) {
	tableNames := []string{"inference_data_events", "study_confs", "studies"}
	query := ""
	for _, table := range tableNames {
		query += fmt.Sprintf("DELETE FROM %s; ", table)
	}

	_, err := pool.Exec(context.Background(), query)
	if err != nil {
		panic(err)
	}
}

func uuid(i int) string {
	return fmt.Sprintf("00000000-0000-0000-0000-00000000000%d", i)
}

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

	resetDb(pool)

	foo := createStudy(pool, "foo", true)
	bar := createStudy(pool, "bar", false)

	mustExec(t, pool, insertConf, foo, "data_source", confA)
	mustExec(t, pool, insertConf, bar, "data_source", confA)

	confs, err := GetStudyConfs(pool, "literacy_data_api")

	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs))
}

func TestGetStudyConfs_GetsOnlyConfsWithCorrectSource(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	resetDb(pool)

	foo := createStudy(pool, "foo", true)

	mustExec(t, pool, insertConf, foo, "data_source", confB)

	confs, err := GetStudyConfs(pool, "literacy_data_api")

	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs))

	params := parseParams(confs[0].Conf.Config)
	assert.Equal(t, "attribution", params.AttributionID)
}

func TestGetStudyConfs_GetsMultipleConfsFromTheSameSource(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	resetDb(pool)

	foo := createStudy(pool, "foo", true)

	mustExec(t, pool, insertConf, foo, "data_source", confD)

	confs, err := GetStudyConfs(pool, "literacy_data_api")

	assert.Nil(t, err)
	assert.Equal(t, 2, len(confs))

	assert.Equal(t, "D1", confs[0].Conf.Name)
	assert.Equal(t, "D2", confs[1].Conf.Name)
}

func TestGetStudyConfs_GetsOnlyTheLatestConfPerStudy(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	resetDb(pool)

	foo := createStudy(pool, "foo", true)

	mustExec(t, pool, insertConf, foo, "data_source", confA)
	mustExec(t, pool, insertConf, foo, "data_source", confC)

	confs, err := GetStudyConfs(pool, "literacy_data_api")

	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs))
	params := parseParams(confs[0].Conf.Config)
	assert.Equal(t, "attribution_later", params.AttributionID)
}

func TestWriteEvents_DoesSomethingReasonable(t *testing.T) {
	// TODO: test.
}

func eventChan(events ...*InferenceDataEvent) <-chan *InferenceDataEvent {
	c := make(chan *InferenceDataEvent)
	go func() {
		defer close(c)
		for _, e := range events {
			c <- e
		}
	}()
	return c
}

func simpleEvent(study, sourceName string, idx int, pagination string) *InferenceDataEvent {
	return &InferenceDataEvent{User{ID: "foo"},
		study,
		&SourceConf{sourceName, "source", []byte(`{"foo": "bar"}`)},
		time.Now(),
		"foo",
		[]byte("100"),
		idx,
		pagination}
}

func TestLastEvent_GetsLatestPaginationToken(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	resetDb(pool)

	foo := createStudy(pool, "foo", true)

	events := eventChan(
		simpleEvent(foo, "sourceA", 0, "0"),
		simpleEvent(foo, "sourceA", 10, "1"),
	)

	WriteEvents(pool, foo, events)

	source := &Source{foo, &SourceConf{"sourceA", "fly", []byte(`{"foo": "bar"}`)}}
	idx, token, ok, err := LastEvent(pool, source)

	assert.Nil(t, err)
	assert.True(t, ok)
	assert.Equal(t, 10, idx)
	assert.Equal(t, "1", token)
}

func TestLastEvent_ReturnsFalseWhenNoEvents(t *testing.T) {
	pool := testPool()
	defer pool.Close()

	resetDb(pool)

	foo := createStudy(pool, "foo", true)

	source := &Source{foo, &SourceConf{"sourceA", "fly", []byte(`{"foo": "bar"}`)}}
	idx, token, ok, err := LastEvent(pool, source)

	assert.Nil(t, err)
	assert.False(t, ok)
	assert.Equal(t, 0, idx)
	assert.Equal(t, "", token)
}
