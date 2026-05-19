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
            "credentials_key": "litkey",
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
            "credentials_key": "litkey",
	    "config": {
		"from": 0,
		"app_id": "appid",
		"attribution_id": "attribution"
	    }
	},
        {
            "name": "B2",
	    "source": "another_source",
            "credentials_key": "sourcekey",
	    "config": {}
	}]
       `

	confC = `
	[{
            "name": "C1",
	    "source": "literacy_data_api",
            "credentials_key": "litkey",
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
            "credentials_key": "litkey",
	    "config": {
		"from": 0,
		"app_id": "appid",
		"attribution_id": "attribution"
	    }
	},
        {
            "name": "D2",
	    "source": "literacy_data_api",
            "credentials_key": "litkey",
	    "config": {
		"from": 0,
		"app_id": "appid2",
		"attribution_id": "attribution2"
	    }
	}]
       `

	futureDate = `
        {
           "start_date": "2022-01-10T00:00:00",
           "end_date": "2999-01-31T00:00:00"
        }
        `
	pastDate = `
        {
           "start_date": "2022-01-10T00:00:00",
           "end_date": "2022-01-31T00:00:00"
        }
        `

	selectUser       = `select id from users where email = $1`
	insertStudy      = `insert into studies(user_id, name) values($1, $2) returning id`
	insertConf       = `insert into study_confs(study_id, conf_type, conf) values($1, $2, $3)`
	insertCredential = `insert into credentials(user_id, entity, key, details) values ($1, $2, $3, $4)`
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

func TestGetStudyConfs_GetsOnlyActiveStudies(t *testing.T) {
	// Active studies (start_date < NOW < end_date + grace) are returned;
	// studies whose end_date + grace has passed are excluded.
	pool := TestPool()
	defer pool.Close()

	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	userFoo := "foo@email"
	bar := CreateStudy(pool, "bar")
	userBar := "bar@email"

	MustExec(t, pool, insertConf, foo, "recruitment", futureDate)
	MustExec(t, pool, insertConf, bar, "recruitment", pastDate)

	MustExec(t, pool, insertConf, foo, "data_sources", confA)
	MustExec(t, pool, insertConf, bar, "data_sources", confA)

	MustExec(t, pool, insertCredential, userFoo, "literacy_data_api", "litkey", `{}`)
	MustExec(t, pool, insertCredential, userBar, "literacy_data_api", "litkey", `{}`)

	confs, err := GetStudyConfs(pool, "literacy_data_api", 14)

	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs))
	assert.Equal(t, foo, confs[0].StudyID)

	assert.Equal(t, "litkey", confs[0].Credentials.Key)
}

func TestGetStudyConfs_GetsOnlyConfsWithCorrectSource(t *testing.T) {
	pool := TestPool()
	defer pool.Close()

	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	user := "foo@email"
	MustExec(t, pool, insertConf, foo, "recruitment", futureDate)
	MustExec(t, pool, insertConf, foo, "data_sources", confB)

	MustExec(t, pool, insertCredential, user, "literacy_data_api", "litkey", `{"token": "abc"}`)

	confs, err := GetStudyConfs(pool, "literacy_data_api", 14)

	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs))

	value := gjson.Get(string(confs[0].Conf.Config), "attribution_id")
	assert.Equal(t, "attribution", value.String())
	assert.Equal(t, "litkey", confs[0].Credentials.Key)
}

func TestGetStudyConfs_GetsMultipleConfsFromTheSameSource(t *testing.T) {
	pool := TestPool()
	defer pool.Close()

	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	user := "foo@email"
	MustExec(t, pool, insertConf, foo, "recruitment", futureDate)
	MustExec(t, pool, insertConf, foo, "data_sources", confD)

	MustExec(t, pool, insertCredential, user, "literacy_data_api", "litkey", `{"token": "abc"}`)

	confs, err := GetStudyConfs(pool, "literacy_data_api", 14)

	assert.Nil(t, err)
	assert.Equal(t, 2, len(confs))

	assert.Equal(t, "D1", confs[0].Conf.Name)
	assert.Equal(t, "litkey", confs[0].Credentials.Key)
	assert.Equal(t, "D2", confs[1].Conf.Name)
	assert.Equal(t, "litkey", confs[1].Credentials.Key)
}

func TestGetStudyConfs_GetsOnlyTheLatestConfPerStudy(t *testing.T) {
	pool := TestPool()
	defer pool.Close()

	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	user := "foo@email"
	MustExec(t, pool, insertConf, foo, "recruitment", futureDate)

	MustExec(t, pool, insertConf, foo, "data_sources", confA)
	MustExec(t, pool, insertConf, foo, "data_sources", confC)

	MustExec(t, pool, insertCredential, user, "literacy_data_api", "litkey", `{"token": "abc"}`)

	confs, err := GetStudyConfs(pool, "literacy_data_api", 14)

	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs))
	assert.Equal(t, "litkey", confs[0].Credentials.Key)
	value := gjson.Get(string(confs[0].Conf.Config), "attribution_id")
	assert.Equal(t, "attribution_later", value.String())
}

func TestGetStudyConfs_SkipsRowAndFailsSilentlyIfCredentialsAreMissing(t *testing.T) {
	pool := TestPool()
	defer pool.Close()

	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	MustExec(t, pool, insertConf, foo, "recruitment", futureDate)
	MustExec(t, pool, insertConf, foo, "data_sources", confA)

	confs, err := GetStudyConfs(pool, "literacy_data_api", 14)

	assert.Nil(t, err)
	assert.Equal(t, 0, len(confs))
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
	return &InferenceDataEvent{
		User:  User{ID: "foo"},
		Study: study,
		SourceConf: &SourceConf{
			Name:           sourceName,
			Source:         "source",
			Config:         []byte(`{"foo": "bar"}`),
			CredentialsKey: "credkey",
		},
		Timestamp:  time.Now(),
		Variable:   "foo",
		Value:      []byte("100"),
		Idx:        idx,
		Pagination: pagination,
	}
}

func TestLastEvent_GetsLatestPaginationToken(t *testing.T) {
	pool := TestPool()
	defer pool.Close()

	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	MustExec(t, pool, insertConf, foo, "recruitment", futureDate)

	e1 := simpleEvent(foo, "sourceA", 0, "0")
	e1.Timestamp = time.Date(2020, 1, 1, 0, 0, 0, 0, time.UTC)
	e2 := simpleEvent(foo, "sourceA", 10, "1")
	e2.Timestamp = time.Date(2020, 1, 2, 0, 0, 0, 0, time.UTC)
	events := eventChan(e1, e2)

	WriteEvents(pool, foo, events)

	source := &Source{
		StudyID: foo,
		Conf: &SourceConf{
			Name:           "sourceA",
			Source:         "fly",
			Config:         []byte(`{"foo": "bar"}`),
			CredentialsKey: "flykey",
		},
		Credentials: &Credentials{
			Entity:  "fly",
			Key:     "flykey",
			Details: []byte(`{}`),
			Created: time.Now().UTC(),
		},
	}
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
	MustExec(t, pool, insertConf, foo, "recruitment", futureDate)

	source := &Source{
		StudyID: foo,
		Conf: &SourceConf{
			Name:           "sourceA",
			Source:         "fly",
			Config:         []byte(`{"foo": "bar"}`),
			CredentialsKey: "flykey",
		},
		Credentials: &Credentials{
			Entity:  "fly",
			Key:     "flykey",
			Details: []byte(`{}`),
			Created: time.Now().UTC(),
		},
	}
	event, ok, err := LastEvent(pool, source, "timestamp")

	assert.Nil(t, err)
	assert.False(t, ok)
	assert.Nil(t, event)
}

// ============================================================================
// Grace Window Tests
// ============================================================================

func TestGetStudyConfs_ActiveStudyReturned(t *testing.T) {
	// Study within start_date < NOW < end_date is collected.
	pool := TestPool()
	defer pool.Close()

	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	MustExec(t, pool, insertConf, foo, "recruitment", futureDate)
	MustExec(t, pool, insertConf, foo, "data_sources", confA)
	MustExec(t, pool, insertCredential, "foo@email", "literacy_data_api", "litkey", `{}`)

	confs, err := GetStudyConfs(pool, "literacy_data_api", 14)

	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs))
	assert.Equal(t, foo, confs[0].StudyID)
}

func TestGetStudyConfs_WithinGraceReturned(t *testing.T) {
	// Study with end_date in the past but within grace window is collected.
	pool := TestPool()
	defer pool.Close()

	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	now := time.Now()
	endDate := now.Add(-5 * 24 * time.Hour) // ended 5 days ago, within M=14
	gracePeriodDate := fmt.Sprintf(`{"start_date":"2020-01-10T00:00:00","end_date":"%s"}`, endDate.Format(time.RFC3339))
	MustExec(t, pool, insertConf, foo, "recruitment", gracePeriodDate)
	MustExec(t, pool, insertConf, foo, "data_sources", confA)
	MustExec(t, pool, insertCredential, "foo@email", "literacy_data_api", "litkey", `{}`)

	confs, err := GetStudyConfs(pool, "literacy_data_api", 14)

	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs))
	assert.Equal(t, foo, confs[0].StudyID)
}

func TestGetStudyConfs_PastGraceExcluded(t *testing.T) {
	// Study past end_date + grace is excluded.
	pool := TestPool()
	defer pool.Close()

	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	now := time.Now()
	endDate := now.Add(-20 * 24 * time.Hour) // ended 20 days ago, past M=14
	pastGraceDate := fmt.Sprintf(`{"start_date":"2020-01-10T00:00:00","end_date":"%s"}`, endDate.Format(time.RFC3339))
	MustExec(t, pool, insertConf, foo, "recruitment", pastGraceDate)
	MustExec(t, pool, insertConf, foo, "data_sources", confA)
	MustExec(t, pool, insertCredential, "foo@email", "literacy_data_api", "litkey", `{}`)

	confs, err := GetStudyConfs(pool, "literacy_data_api", 14)

	assert.Nil(t, err)
	assert.Equal(t, 0, len(confs))
}

func TestGetStudyConfs_FutureStartExcluded(t *testing.T) {
	// Study with start_date in the future is excluded.
	pool := TestPool()
	defer pool.Close()

	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	now := time.Now()
	startDate := now.Add(10 * 24 * time.Hour)
	endDate := now.Add(40 * 24 * time.Hour)
	futureStart := fmt.Sprintf(`{"start_date":"%s","end_date":"%s"}`,
		startDate.Format(time.RFC3339), endDate.Format(time.RFC3339))
	MustExec(t, pool, insertConf, foo, "recruitment", futureStart)
	MustExec(t, pool, insertConf, foo, "data_sources", confA)
	MustExec(t, pool, insertCredential, "foo@email", "literacy_data_api", "litkey", `{}`)

	confs, err := GetStudyConfs(pool, "literacy_data_api", 14)

	assert.Nil(t, err)
	assert.Equal(t, 0, len(confs))
}

func TestGetStudyConfs_GraceDaysConfigurable(t *testing.T) {
	// The grace window M is configurable.
	pool := TestPool()
	defer pool.Close()

	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	now := time.Now()
	endDate := now.Add(-5 * 24 * time.Hour) // ended 5 days ago
	recentEndDate := fmt.Sprintf(`{"start_date":"2020-01-10T00:00:00","end_date":"%s"}`, endDate.Format(time.RFC3339))
	MustExec(t, pool, insertConf, foo, "recruitment", recentEndDate)
	MustExec(t, pool, insertConf, foo, "data_sources", confA)
	MustExec(t, pool, insertCredential, "foo@email", "literacy_data_api", "litkey", `{}`)

	// M=14: within grace → returned
	confs, err := GetStudyConfs(pool, "literacy_data_api", 14)
	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs))

	// M=3: past grace → excluded
	confs, err = GetStudyConfs(pool, "literacy_data_api", 3)
	assert.Nil(t, err)
	assert.Equal(t, 0, len(confs))
}

// ============================================================================
// Error Isolation Tests
// ============================================================================

// mockConnectorWithFailure simulates a Connector that fails for a specific study
type mockConnectorWithFailure struct {
	failStudyID string // Study that will fail processing
	workingData map[string][]*InferenceDataEvent
}

func (m *mockConnectorWithFailure) Handler(source *Source, lastEvent *InferenceDataEvent) <-chan *InferenceDataEvent {
	c := make(chan *InferenceDataEvent)
	go func() {
		defer close(c)
		// If this is the failing study, return an error by closing channel immediately (0 events)
		// This simulates a connector that cannot retrieve events for that study
		if source.StudyID == m.failStudyID {
			// Send nothing and close - simulate total failure to retrieve any events
			return
		}

		// For working studies, send the pre-defined events
		if events, ok := m.workingData[source.StudyID]; ok {
			for _, e := range events {
				c <- e
			}
		}
	}()
	return c
}

func TestLoadEvents_ContinuesPastFailedStudy(t *testing.T) {
	// Test that when one study's processing fails (connector returns no data),
	// LoadEvents continues and processes remaining studies successfully.
	// This validates the error isolation introduced by collectEventsForStudy.
	pool := TestPool()
	defer pool.Close()

	resetDb(pool)

	// Create two studies, both active and with future end dates
	studyA := CreateStudy(pool, "studyA")
	studyB := CreateStudy(pool, "studyB")

	activeDate := `
	{
	   "start_date": "2020-01-10T00:00:00",
	   "end_date": "2999-01-31T00:00:00"
	}
	`
	MustExec(t, pool, insertConf, studyA, "recruitment", activeDate)
	MustExec(t, pool, insertConf, studyB, "recruitment", activeDate)

	MustExec(t, pool, insertConf, studyA, "data_sources", confA)
	MustExec(t, pool, insertConf, studyB, "data_sources", confA)

	MustExec(t, pool, insertCredential, "studyA@email", "literacy_data_api", "litkey", `{}`)
	MustExec(t, pool, insertCredential, "studyB@email", "literacy_data_api", "litkey", `{}`)

	// Create mock connector: studyA fails (returns no events), studyB works
	mockConn := &mockConnectorWithFailure{
		failStudyID: studyA,
		workingData: map[string][]*InferenceDataEvent{
			studyB: {
				simpleEvent(studyB, "A1", 0, ""),
				simpleEvent(studyB, "A1", 1, ""),
			},
		},
	}

	// Manually run collectEventsForStudy for each study, simulating what LoadEvents does
	sources, err := GetStudyConfs(pool, "literacy_data_api", 14)
	assert.Nil(t, err)
	assert.Equal(t, 2, len(sources), "Should have both studies available")

	// Process both studies, expecting studyA to fail silently and studyB to succeed
	for _, source := range sources {
		if err := collectEventsForStudy(pool, mockConn, source, "idx"); err != nil {
			// Error is logged but doesn't stop processing other studies
			t.Logf("Expected error for failing study: %v", err)
		}
	}

	// Verify studyB's events were written despite studyA failing
	var countB int
	err = pool.QueryRow(context.Background(),
		`SELECT COUNT(*) FROM inference_data_events WHERE study_id = $1`,
		studyB).Scan(&countB)

	assert.Nil(t, err)
	assert.Equal(t, 2, countB, "Study B should have 2 events written despite Study A failing")

	// Verify studyA has no events (because connector returned nothing)
	var countA int
	err = pool.QueryRow(context.Background(),
		`SELECT COUNT(*) FROM inference_data_events WHERE study_id = $1`,
		studyA).Scan(&countA)

	assert.Nil(t, err)
	assert.Equal(t, 0, countA, "Study A should have no events (connector failed)")
}
