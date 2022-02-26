package connector

import (
	"context"
	"fmt"
	"github.com/jackc/pgx/v4/pgxpool"
	"github.com/stretchr/testify/assert"
	"github.com/tidwall/gjson"
	. "github.com/vlab-research/vlab/inference/inference-data"
	. "github.com/vlab-research/vlab/inference/test-helpers"
	"testing"
	"time"
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

	futureDate = `
        [{
           "start_date": "2022-01-10T00:00:00",
           "end_date": "2999-01-31T00:00:00"
        }]
        `
	pastDate = `
        [{
           "start_date": "2022-01-10T00:00:00",
           "end_date": "2022-01-31T00:00:00"
        }]
        `

	insertUser  = `insert into users(email) values($1) returning id`
	selectUser  = `select id from users where email = $1`
	insertStudy = `insert into studies(user_id, name) values($1, $2) returning id`
	insertConf  = `insert into study_confs(study_id, conf_type, conf) values($1, $2, $3)`
)

func resetDb(pool *pgxpool.Pool) {
	tableNames := []string{"inference_data_events", "study_confs", "studies", "users"}
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

func TestGetStudyConfs_GetsOnlyActiveStudies(t *testing.T) {
	pool := TestPool()
	defer pool.Close()

	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	bar := CreateStudy(pool, "bar")

	MustExec(t, pool, insertConf, foo, "opt", futureDate)
	MustExec(t, pool, insertConf, bar, "opt", pastDate)

	MustExec(t, pool, insertConf, foo, "data_source", confA)
	MustExec(t, pool, insertConf, bar, "data_source", confA)

	confs, err := GetStudyConfs(pool, "literacy_data_api")

	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs))
	assert.Equal(t, foo, confs[0].StudyID)
}

func TestGetStudyConfs_GetsOnlyConfsWithCorrectSource(t *testing.T) {
	pool := TestPool()
	defer pool.Close()

	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	MustExec(t, pool, insertConf, foo, "opt", futureDate)
	MustExec(t, pool, insertConf, foo, "data_source", confB)

	confs, err := GetStudyConfs(pool, "literacy_data_api")

	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs))

	value := gjson.Get(string(confs[0].Conf.Config), "attribution_id")
	assert.Equal(t, "attribution", value.String())
}

func TestGetStudyConfs_GetsMultipleConfsFromTheSameSource(t *testing.T) {
	pool := TestPool()
	defer pool.Close()

	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	MustExec(t, pool, insertConf, foo, "opt", futureDate)

	MustExec(t, pool, insertConf, foo, "data_source", confD)

	confs, err := GetStudyConfs(pool, "literacy_data_api")

	assert.Nil(t, err)
	assert.Equal(t, 2, len(confs))

	assert.Equal(t, "D1", confs[0].Conf.Name)
	assert.Equal(t, "D2", confs[1].Conf.Name)
}

func TestGetStudyConfs_GetsOnlyTheLatestConfPerStudy(t *testing.T) {
	pool := TestPool()
	defer pool.Close()

	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	MustExec(t, pool, insertConf, foo, "opt", futureDate)

	MustExec(t, pool, insertConf, foo, "data_source", confA)
	MustExec(t, pool, insertConf, foo, "data_source", confC)

	confs, err := GetStudyConfs(pool, "literacy_data_api")

	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs))
	value := gjson.Get(string(confs[0].Conf.Config), "attribution_id")
	assert.Equal(t, "attribution_later", value.String())
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
	pool := TestPool()
	defer pool.Close()

	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	MustExec(t, pool, insertConf, foo, "opt", futureDate)

	events := eventChan(
		simpleEvent(foo, "sourceA", 0, "0"),
		simpleEvent(foo, "sourceA", 10, "1"),
	)

	WriteEvents(pool, foo, events)

	source := &Source{foo, &SourceConf{"sourceA", "fly", []byte(`{"foo": "bar"}`)}}
	event, ok, err := LastEvent(pool, source, "timestamp")

	assert.Nil(t, err)
	assert.True(t, ok)
	assert.Equal(t, 10, event.Idx)
	assert.Equal(t, "1", event.Pagination)
}

func TestLastEvent_ReturnsFalseWhenNoEvents(t *testing.T) {
	pool := TestPool()
	defer pool.Close()

	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	MustExec(t, pool, insertConf, foo, "opt", futureDate)

	source := &Source{foo, &SourceConf{"sourceA", "fly", []byte(`{"foo": "bar"}`)}}
	event, ok, err := LastEvent(pool, source, "timestamp")

	assert.Nil(t, err)
	assert.False(t, ok)
	assert.Nil(t, event)
}
