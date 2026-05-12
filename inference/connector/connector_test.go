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

func initConnectorRunsTable(pool *pgxpool.Pool) {
	// Drop and recreate connector_runs table to ensure correct schema
	dropQuery := `DROP TABLE IF EXISTS connector_runs;`
	_, err := pool.Exec(context.Background(), dropQuery)
	if err != nil {
		panic(fmt.Sprintf("Failed to drop connector_runs table: %v", err))
	}

	// Create connector_runs table with correct schema
	createTableQuery := `
	CREATE TABLE connector_runs (
	  study_id    UUID NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
	  source_name TEXT NOT NULL,
	  run_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	  events_written INTEGER NOT NULL
	);

	CREATE INDEX idx_connector_runs_lookup
	  ON connector_runs (study_id, source_name, run_at DESC);
	`
	_, err = pool.Exec(context.Background(), createTableQuery)
	if err != nil {
		panic(fmt.Sprintf("Failed to create connector_runs table: %v", err))
	}
}

func resetDb(pool *pgxpool.Pool) {
	tableNames := []string{"inference_data_events", "connector_runs", "study_confs", "studies", "users"}
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
	// Regression test: ensure active studies are returned and quiescent ones are not
	pool := TestPool()
	defer pool.Close()

	initConnectorRunsTable(pool)
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

	// Add K consecutive zero runs to bar to make it quiescent
	insertConnectorRun(t, pool, bar, "A1", 0)
	insertConnectorRun(t, pool, bar, "A1", 0)
	insertConnectorRun(t, pool, bar, "A1", 0)

	confs, err := GetStudyConfs(pool, "literacy_data_api", 14, 3)

	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs))
	assert.Equal(t, foo, confs[0].StudyID)

	assert.Equal(t, "litkey", confs[0].Credentials.Key)
}

func TestGetStudyConfs_GetsOnlyConfsWithCorrectSource(t *testing.T) {
	pool := TestPool()
	defer pool.Close()

 initConnectorRunsTable(pool)
	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	user := "foo@email"
	MustExec(t, pool, insertConf, foo, "recruitment", futureDate)
	MustExec(t, pool, insertConf, foo, "data_sources", confB)

	MustExec(t, pool, insertCredential, user, "literacy_data_api", "litkey", `{"token": "abc"}`)

	confs, err := GetStudyConfs(pool, "literacy_data_api", 14, 3)

	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs))

	value := gjson.Get(string(confs[0].Conf.Config), "attribution_id")
	assert.Equal(t, "attribution", value.String())
	assert.Equal(t, "litkey", confs[0].Credentials.Key)
}

func TestGetStudyConfs_GetsMultipleConfsFromTheSameSource(t *testing.T) {
	pool := TestPool()
	defer pool.Close()

 initConnectorRunsTable(pool)
	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	user := "foo@email"
	MustExec(t, pool, insertConf, foo, "recruitment", futureDate)
	MustExec(t, pool, insertConf, foo, "data_sources", confD)

	MustExec(t, pool, insertCredential, user, "literacy_data_api", "litkey", `{"token": "abc"}`)

	confs, err := GetStudyConfs(pool, "literacy_data_api", 14, 3)

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

 initConnectorRunsTable(pool)
	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	user := "foo@email"
	MustExec(t, pool, insertConf, foo, "recruitment", futureDate)

	MustExec(t, pool, insertConf, foo, "data_sources", confA)
	MustExec(t, pool, insertConf, foo, "data_sources", confC)

	MustExec(t, pool, insertCredential, user, "literacy_data_api", "litkey", `{"token": "abc"}`)

	confs, err := GetStudyConfs(pool, "literacy_data_api", 14, 3)

	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs))
	assert.Equal(t, "litkey", confs[0].Credentials.Key)
	value := gjson.Get(string(confs[0].Conf.Config), "attribution_id")
	assert.Equal(t, "attribution_later", value.String())
}

func TestGetStudyConfs_SkipsRowAndFailsSilentlyIfCredentialsAreMissing(t *testing.T) {
	pool := TestPool()
	defer pool.Close()

 initConnectorRunsTable(pool)
	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	MustExec(t, pool, insertConf, foo, "recruitment", futureDate)
	MustExec(t, pool, insertConf, foo, "data_sources", confA)

	confs, err := GetStudyConfs(pool, "literacy_data_api", 14, 3)

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
		User:       User{ID: "foo"},
		Study:      study,
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

 initConnectorRunsTable(pool)
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

 initConnectorRunsTable(pool)
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
// Quiescence Feature Tests
// ============================================================================

func insertConnectorRun(t *testing.T, pool *pgxpool.Pool, studyID string, sourceName string, eventsWritten int) {
	query := `INSERT INTO connector_runs (study_id, source_name, events_written) VALUES ($1, $2, $3)`
	MustExec(t, pool, query, studyID, sourceName, eventsWritten)
}

func TestGetStudyConfs_Zone2_ActiveStudyAlwaysReturned(t *testing.T) {
	// Zone 2 (active): study within start_date < NOW < end_date is returned
	// even with many zero-event runs in connector_runs
	pool := TestPool()
	defer pool.Close()

	initConnectorRunsTable(pool)
	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	userFoo := "foo@email"

	// Create a study that is currently active (start < NOW < end)
	activeDate := `
	{
	   "start_date": "2020-01-10T00:00:00",
	   "end_date": "2999-01-31T00:00:00"
	}
	`
	MustExec(t, pool, insertConf, foo, "recruitment", activeDate)
	MustExec(t, pool, insertConf, foo, "data_sources", confA)
	MustExec(t, pool, insertCredential, userFoo, "literacy_data_api", "litkey", `{}`)

	// Add many zero-event connector_runs (would be quiescent in other zones)
	insertConnectorRun(t, pool, foo, "A1", 0)
	insertConnectorRun(t, pool, foo, "A1", 0)
	insertConnectorRun(t, pool, foo, "A1", 0)
	insertConnectorRun(t, pool, foo, "A1", 0)
	insertConnectorRun(t, pool, foo, "A1", 0)

	// Despite the zero-event runs, study should be returned because it's in Zone 2 (active)
	confs, err := GetStudyConfs(pool, "literacy_data_api", 14, 3)

	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs))
	assert.Equal(t, foo, confs[0].StudyID)
}

func TestGetStudyConfs_Zone3_GracePeriodAlwaysReturned(t *testing.T) {
	// Zone 3 (grace period): study past end_date but within M days is returned
	// regardless of connector_runs
	pool := TestPool()
	defer pool.Close()

	initConnectorRunsTable(pool)
	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	userFoo := "foo@email"

	// Create study that ended 5 days ago (within 14-day grace period)
	now := time.Now()
	endDate := now.Add(-5 * 24 * time.Hour)
	gracePeriodDate := fmt.Sprintf(`
	{
	   "start_date": "2020-01-10T00:00:00",
	   "end_date": "%s"
	}
	`, endDate.Format(time.RFC3339))

	MustExec(t, pool, insertConf, foo, "recruitment", gracePeriodDate)
	MustExec(t, pool, insertConf, foo, "data_sources", confA)
	MustExec(t, pool, insertCredential, userFoo, "literacy_data_api", "litkey", `{}`)

	// Add zero-event runs (would trigger quiescence if past grace period)
	insertConnectorRun(t, pool, foo, "A1", 0)
	insertConnectorRun(t, pool, foo, "A1", 0)
	insertConnectorRun(t, pool, foo, "A1", 0)

	// Study should be returned because it's in grace period, regardless of zero runs
	confs, err := GetStudyConfs(pool, "literacy_data_api", 14, 3)

	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs))
	assert.Equal(t, foo, confs[0].StudyID)
}

func TestGetStudyConfs_Zone4_QuiescentStudyExcluded(t *testing.T) {
	// Zone 4 (quiescent): study past end_date+M with K or more consecutive zero runs is excluded
	pool := TestPool()
	defer pool.Close()

	initConnectorRunsTable(pool)
	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	userFoo := "foo@email"

	// Create study that ended 20 days ago (past 14-day grace period)
	now := time.Now()
	endDate := now.Add(-20 * 24 * time.Hour)
	pastGracePeriodDate := fmt.Sprintf(`
	{
	   "start_date": "2020-01-10T00:00:00",
	   "end_date": "%s"
	}
	`, endDate.Format(time.RFC3339))

	MustExec(t, pool, insertConf, foo, "recruitment", pastGracePeriodDate)
	MustExec(t, pool, insertConf, foo, "data_sources", confA)
	MustExec(t, pool, insertCredential, userFoo, "literacy_data_api", "litkey", `{}`)

	// Add K=3 consecutive zero-event runs (quiescent)
	insertConnectorRun(t, pool, foo, "A1", 0)
	insertConnectorRun(t, pool, foo, "A1", 0)
	insertConnectorRun(t, pool, foo, "A1", 0)

	// Study should NOT be returned because it's quiescent (K consecutive zeros past grace period)
	confs, err := GetStudyConfs(pool, "literacy_data_api", 14, 3)

	assert.Nil(t, err)
	assert.Equal(t, 0, len(confs))
}

func TestGetStudyConfs_Zone5_NotQuiescentPastGracePeriod(t *testing.T) {
	// Zone 5 (not quiescent): study past end_date+M with fewer than K zero runs is still returned
	pool := TestPool()
	defer pool.Close()

	initConnectorRunsTable(pool)
	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	userFoo := "foo@email"

	// Create study that ended 20 days ago (past 14-day grace period)
	now := time.Now()
	endDate := now.Add(-20 * 24 * time.Hour)
	pastGracePeriodDate := fmt.Sprintf(`
	{
	   "start_date": "2020-01-10T00:00:00",
	   "end_date": "%s"
	}
	`, endDate.Format(time.RFC3339))

	MustExec(t, pool, insertConf, foo, "recruitment", pastGracePeriodDate)
	MustExec(t, pool, insertConf, foo, "data_sources", confA)
	MustExec(t, pool, insertCredential, userFoo, "literacy_data_api", "litkey", `{}`)

	// Add K-1=2 zero-event runs plus one non-zero run (not quiescent)
	insertConnectorRun(t, pool, foo, "A1", 0)
	insertConnectorRun(t, pool, foo, "A1", 0)
	insertConnectorRun(t, pool, foo, "A1", 5)

	// Study should be returned because not all last K runs are zeros (has at least one non-zero)
	confs, err := GetStudyConfs(pool, "literacy_data_api", 14, 3)

	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs))
	assert.Equal(t, foo, confs[0].StudyID)
}

func TestGetStudyConfs_Zone5_BreakStreakWithNonZero(t *testing.T) {
	// Zone 4-5 boundary: K-1 zeros followed by one non-zero run breaks the quiescence streak
	pool := TestPool()
	defer pool.Close()

	initConnectorRunsTable(pool)
	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	userFoo := "foo@email"

	// Create study that ended 20 days ago (past grace period)
	now := time.Now()
	endDate := now.Add(-20 * 24 * time.Hour)
	pastGracePeriodDate := fmt.Sprintf(`
	{
	   "start_date": "2020-01-10T00:00:00",
	   "end_date": "%s"
	}
	`, endDate.Format(time.RFC3339))

	MustExec(t, pool, insertConf, foo, "recruitment", pastGracePeriodDate)
	MustExec(t, pool, insertConf, foo, "data_sources", confA)
	MustExec(t, pool, insertCredential, userFoo, "literacy_data_api", "litkey", `{}`)

	// Add runs: non-zero, then K-1 zeros (ordered by most recent last)
	insertConnectorRun(t, pool, foo, "A1", 0)
	insertConnectorRun(t, pool, foo, "A1", 0)
	insertConnectorRun(t, pool, foo, "A1", 10)

	// Most recent K=3 runs: [10, 0, 0] - has non-zero, so NOT quiescent
	confs, err := GetStudyConfs(pool, "literacy_data_api", 14, 3)

	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs))
	assert.Equal(t, foo, confs[0].StudyID)
}

func TestGetStudyConfs_Zone5_AutoReactivationWhenEndDateExtended(t *testing.T) {
	// Auto-reactivation: if a study's end_date is extended back into active zone,
	// it should be automatically returned (no reset flag needed)
	pool := TestPool()
	defer pool.Close()

	initConnectorRunsTable(pool)
	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	userFoo := "foo@email"

	// Start with a study that ended 20 days ago (quiescent)
	now := time.Now()
	endDate := now.Add(-20 * 24 * time.Hour)
	pastGracePeriodDate := fmt.Sprintf(`
	{
	   "start_date": "2020-01-10T00:00:00",
	   "end_date": "%s"
	}
	`, endDate.Format(time.RFC3339))

	MustExec(t, pool, insertConf, foo, "recruitment", pastGracePeriodDate)
	MustExec(t, pool, insertConf, foo, "data_sources", confA)
	MustExec(t, pool, insertCredential, userFoo, "literacy_data_api", "litkey", `{}`)

	// Add K=3 consecutive zero runs
	insertConnectorRun(t, pool, foo, "A1", 0)
	insertConnectorRun(t, pool, foo, "A1", 0)
	insertConnectorRun(t, pool, foo, "A1", 0)

	// Verify study is quiescent
	confs, err := GetStudyConfs(pool, "literacy_data_api", 14, 3)
	assert.Nil(t, err)
	assert.Equal(t, 0, len(confs))

	// Now extend end_date to future (NOW + 10 days)
	newEndDate := now.Add(10 * 24 * time.Hour)
	extendedDate := fmt.Sprintf(`
	{
	   "start_date": "2020-01-10T00:00:00",
	   "end_date": "%s"
	}
	`, newEndDate.Format(time.RFC3339))

	MustExec(t, pool, insertConf, foo, "recruitment", extendedDate)

	// Study should now be returned because end_date is extended into future (Zone 2-3)
	confs, err = GetStudyConfs(pool, "literacy_data_api", 14, 3)

	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs))
	assert.Equal(t, foo, confs[0].StudyID)
}

func TestGetStudyConfs_MultipleSourcesSameStyudyTracksSeparately(t *testing.T) {
	// Different sources for the same study should track their quiescence separately
	pool := TestPool()
	defer pool.Close()

 initConnectorRunsTable(pool)
	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	userFoo := "foo@email"

	// Create study that ended 20 days ago (past grace period)
	now := time.Now()
	endDate := now.Add(-20 * 24 * time.Hour)
	pastGracePeriodDate := fmt.Sprintf(`
	{
	   "start_date": "2020-01-10T00:00:00",
	   "end_date": "%s"
	}
	`, endDate.Format(time.RFC3339))

	MustExec(t, pool, insertConf, foo, "recruitment", pastGracePeriodDate)
	// Use confD which has two sources: D1 and D2
	MustExec(t, pool, insertConf, foo, "data_sources", confD)
	MustExec(t, pool, insertCredential, userFoo, "literacy_data_api", "litkey", `{}`)

	// Source D1: K=3 consecutive zero runs (quiescent)
	insertConnectorRun(t, pool, foo, "D1", 0)
	insertConnectorRun(t, pool, foo, "D1", 0)
	insertConnectorRun(t, pool, foo, "D1", 0)

	// Source D2: K-1=2 zero runs and 1 non-zero (not quiescent)
	insertConnectorRun(t, pool, foo, "D2", 0)
	insertConnectorRun(t, pool, foo, "D2", 0)
	insertConnectorRun(t, pool, foo, "D2", 5)

	confs, err := GetStudyConfs(pool, "literacy_data_api", 14, 3)

	assert.Nil(t, err)
	// Should only return D2 (D1 is quiescent)
	assert.Equal(t, 1, len(confs))
	assert.Equal(t, "D2", confs[0].Conf.Name)
}

func TestGetStudyConfs_FewerThanKRunsAvailableIsNotQuiescent(t *testing.T) {
	// If there are fewer than K total runs, the study is not yet quiescent
	pool := TestPool()
	defer pool.Close()

 initConnectorRunsTable(pool)
	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	userFoo := "foo@email"

	// Create study past grace period
	now := time.Now()
	endDate := now.Add(-20 * 24 * time.Hour)
	pastGracePeriodDate := fmt.Sprintf(`
	{
	   "start_date": "2020-01-10T00:00:00",
	   "end_date": "%s"
	}
	`, endDate.Format(time.RFC3339))

	MustExec(t, pool, insertConf, foo, "recruitment", pastGracePeriodDate)
	MustExec(t, pool, insertConf, foo, "data_sources", confA)
	MustExec(t, pool, insertCredential, userFoo, "literacy_data_api", "litkey", `{}`)

	// Add only K-1=2 zero runs (fewer than K)
	insertConnectorRun(t, pool, foo, "A1", 0)
	insertConnectorRun(t, pool, foo, "A1", 0)

	// Study should be returned because we don't have K consecutive zeros yet
	confs, err := GetStudyConfs(pool, "literacy_data_api", 14, 3)

	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs))
	assert.Equal(t, foo, confs[0].StudyID)
}

func TestGetStudyConfs_ExactlyKZeroRunsIsQuiescent(t *testing.T) {
	// Edge case: exactly K consecutive zero runs should make study quiescent
	pool := TestPool()
	defer pool.Close()

 initConnectorRunsTable(pool)
	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	userFoo := "foo@email"

	// Create study past grace period
	now := time.Now()
	endDate := now.Add(-20 * 24 * time.Hour)
	pastGracePeriodDate := fmt.Sprintf(`
	{
	   "start_date": "2020-01-10T00:00:00",
	   "end_date": "%s"
	}
	`, endDate.Format(time.RFC3339))

	MustExec(t, pool, insertConf, foo, "recruitment", pastGracePeriodDate)
	MustExec(t, pool, insertConf, foo, "data_sources", confA)
	MustExec(t, pool, insertCredential, userFoo, "literacy_data_api", "litkey", `{}`)

	// Add exactly K=3 zero runs
	insertConnectorRun(t, pool, foo, "A1", 0)
	insertConnectorRun(t, pool, foo, "A1", 0)
	insertConnectorRun(t, pool, foo, "A1", 0)

	// Study should be excluded (quiescent)
	confs, err := GetStudyConfs(pool, "literacy_data_api", 14, 3)

	assert.Nil(t, err)
	assert.Equal(t, 0, len(confs))
}

func TestGetStudyConfs_QuiescenceThresholdRespectsDifferentK(t *testing.T) {
	// Verify that the threshold K is configurable and respected
	pool := TestPool()
	defer pool.Close()

 initConnectorRunsTable(pool)
	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	userFoo := "foo@email"

	// Create study past grace period
	now := time.Now()
	endDate := now.Add(-20 * 24 * time.Hour)
	pastGracePeriodDate := fmt.Sprintf(`
	{
	   "start_date": "2020-01-10T00:00:00",
	   "end_date": "%s"
	}
	`, endDate.Format(time.RFC3339))

	MustExec(t, pool, insertConf, foo, "recruitment", pastGracePeriodDate)
	MustExec(t, pool, insertConf, foo, "data_sources", confA)
	MustExec(t, pool, insertCredential, userFoo, "literacy_data_api", "litkey", `{}`)

	// Add 2 zero runs
	insertConnectorRun(t, pool, foo, "A1", 0)
	insertConnectorRun(t, pool, foo, "A1", 0)

	// With K=3: should be returned (only 2 zeros)
	confs, err := GetStudyConfs(pool, "literacy_data_api", 14, 3)
	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs))

	// With K=2: should be excluded (exactly 2 zeros)
	confs, err = GetStudyConfs(pool, "literacy_data_api", 14, 2)
	assert.Nil(t, err)
	assert.Equal(t, 0, len(confs))

	// With K=1: should be excluded (2 >= 1)
	confs, err = GetStudyConfs(pool, "literacy_data_api", 14, 1)
	assert.Nil(t, err)
	assert.Equal(t, 0, len(confs))
}

func TestGetStudyConfs_GracePeriodRespectsDifferentM(t *testing.T) {
	// Verify that the grace period M is configurable and respected
	pool := TestPool()
	defer pool.Close()

 initConnectorRunsTable(pool)
	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	userFoo := "foo@email"

	// Create study that ended 5 days ago
	now := time.Now()
	endDate := now.Add(-5 * 24 * time.Hour)
	recentEndDate := fmt.Sprintf(`
	{
	   "start_date": "2020-01-10T00:00:00",
	   "end_date": "%s"
	}
	`, endDate.Format(time.RFC3339))

	MustExec(t, pool, insertConf, foo, "recruitment", recentEndDate)
	MustExec(t, pool, insertConf, foo, "data_sources", confA)
	MustExec(t, pool, insertCredential, userFoo, "literacy_data_api", "litkey", `{}`)

	// Add K consecutive zeros
	insertConnectorRun(t, pool, foo, "A1", 0)
	insertConnectorRun(t, pool, foo, "A1", 0)
	insertConnectorRun(t, pool, foo, "A1", 0)

	// With M=14 days: should be returned (within grace period)
	confs, err := GetStudyConfs(pool, "literacy_data_api", 14, 3)
	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs))

	// With M=3 days: should be excluded (past grace period, quiescent)
	confs, err = GetStudyConfs(pool, "literacy_data_api", 3, 3)
	assert.Nil(t, err)
	assert.Equal(t, 0, len(confs))

	// Sub-case 1: M=5 with 4-day-old study → clearly within grace period
	resetDb(pool)
	foo2 := CreateStudy(pool, "foo2")
	endDate4 := now.Add(-4 * 24 * time.Hour)
	within5DaysDate := fmt.Sprintf(`
	{
	   "start_date": "2020-01-10T00:00:00",
	   "end_date": "%s"
	}
	`, endDate4.Format(time.RFC3339))
	MustExec(t, pool, insertConf, foo2, "recruitment", within5DaysDate)
	MustExec(t, pool, insertConf, foo2, "data_sources", confA)
	MustExec(t, pool, insertCredential, "foo2@email", "literacy_data_api", "litkey", `{}`)
	insertConnectorRun(t, pool, foo2, "A1", 0)
	insertConnectorRun(t, pool, foo2, "A1", 0)
	insertConnectorRun(t, pool, foo2, "A1", 0)

	confs, err = GetStudyConfs(pool, "literacy_data_api", 5, 3)
	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs), "Study ended 4 days ago should be within M=5 grace period")

	// Sub-case 2: M=5 with 6-day-old study → clearly past grace period, quiescent
	resetDb(pool)
	foo3 := CreateStudy(pool, "foo3")
	endDate6 := now.Add(-6 * 24 * time.Hour)
	past5DaysDate := fmt.Sprintf(`
	{
	   "start_date": "2020-01-10T00:00:00",
	   "end_date": "%s"
	}
	`, endDate6.Format(time.RFC3339))
	MustExec(t, pool, insertConf, foo3, "recruitment", past5DaysDate)
	MustExec(t, pool, insertConf, foo3, "data_sources", confA)
	MustExec(t, pool, insertCredential, "foo3@email", "literacy_data_api", "litkey", `{}`)
	insertConnectorRun(t, pool, foo3, "A1", 0)
	insertConnectorRun(t, pool, foo3, "A1", 0)
	insertConnectorRun(t, pool, foo3, "A1", 0)

	confs, err = GetStudyConfs(pool, "literacy_data_api", 5, 3)
	assert.Nil(t, err)
	assert.Equal(t, 0, len(confs), "Study ended 6 days ago should be past M=5 grace period with K consecutive zeros")
}

func TestGetStudyConfs_NoConnectorRunsRecordsIsNotQuiescent(t *testing.T) {
	// If a study has no connector_runs records, it should not be treated as quiescent
	pool := TestPool()
	defer pool.Close()

 initConnectorRunsTable(pool)
	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	userFoo := "foo@email"

	// Create study past grace period
	now := time.Now()
	endDate := now.Add(-20 * 24 * time.Hour)
	pastGracePeriodDate := fmt.Sprintf(`
	{
	   "start_date": "2020-01-10T00:00:00",
	   "end_date": "%s"
	}
	`, endDate.Format(time.RFC3339))

	MustExec(t, pool, insertConf, foo, "recruitment", pastGracePeriodDate)
	MustExec(t, pool, insertConf, foo, "data_sources", confA)
	MustExec(t, pool, insertCredential, userFoo, "literacy_data_api", "litkey", `{}`)

	// Do NOT add any connector_runs records

	// Study should be returned because no K consecutive zeros exist
	confs, err := GetStudyConfs(pool, "literacy_data_api", 14, 3)

	assert.Nil(t, err)
	assert.Equal(t, 1, len(confs))
	assert.Equal(t, foo, confs[0].StudyID)
}

// ============================================================================
// recordRun Integration Tests
// ============================================================================

func TestRecordRun_InsertsConnectorRunRow(t *testing.T) {
	// Test that recordRun inserts a row into connector_runs
	pool := TestPool()
	defer pool.Close()

	initConnectorRunsTable(pool)
	resetDb(pool)

	foo := CreateStudy(pool, "foo")
	userFoo := "foo@email"

	activeDate := `
	{
	   "start_date": "2020-01-10T00:00:00",
	   "end_date": "2999-01-31T00:00:00"
	}
	`
	MustExec(t, pool, insertConf, foo, "recruitment", activeDate)
	MustExec(t, pool, insertConf, foo, "data_sources", confA)
	MustExec(t, pool, insertCredential, userFoo, "literacy_data_api", "litkey", `{}`)

	source := &Source{
		StudyID: foo,
		Conf: &SourceConf{
			Name:           "A1",
			Source:         "literacy_data_api",
			Config:         []byte(`{"from": 0}`),
			CredentialsKey: "litkey",
		},
		Credentials: &Credentials{
			Entity:  "literacy_data_api",
			Key:     "litkey",
			Details: []byte(`{}`),
			Created: time.Now().UTC(),
		},
	}

	// Record a run with 5 events written
	err := recordRun(pool, source, 5)

	assert.Nil(t, err)

	// Verify the row was inserted
	var count int
	var eventsWritten int
	query := `SELECT COUNT(*), COALESCE(SUM(events_written), 0) FROM connector_runs WHERE study_id = $1 AND source_name = $2`
	err = pool.QueryRow(context.Background(), query, foo, "A1").Scan(&count, &eventsWritten)

	assert.Nil(t, err)
	assert.Equal(t, 1, count)
	assert.Equal(t, 5, eventsWritten)
}

func TestRecordRun_WarningWhenFailed(t *testing.T) {
	// Test that recordRun handles errors gracefully (warning, not fatal)
	pool := TestPool()
	defer pool.Close()

	initConnectorRunsTable(pool)
	resetDb(pool)

	// Create source with non-existent study ID (will cause FK constraint error)
	source := &Source{
		StudyID: "00000000-0000-0000-0000-000000000000", // Non-existent UUID
		Conf: &SourceConf{
			Name:           "A1",
			Source:         "literacy_data_api",
			Config:         []byte(`{"from": 0}`),
			CredentialsKey: "litkey",
		},
		Credentials: &Credentials{
			Entity:  "literacy_data_api",
			Key:     "litkey",
			Details: []byte(`{}`),
			Created: time.Now().UTC(),
		},
	}

	// recordRun should return an error (not panic)
	err := recordRun(pool, source, 5)

	assert.NotNil(t, err)
	// The function should handle this gracefully - in actual usage, it logs a warning
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

	initConnectorRunsTable(pool)
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
	sources, err := GetStudyConfs(pool, "literacy_data_api", 14, 3)
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

	// Verify that recordRun was called for both studies (even for the failing one with 0 events)
	var runsA, runsB int
	err = pool.QueryRow(context.Background(),
		`SELECT COUNT(*) FROM connector_runs WHERE study_id = $1`,
		studyA).Scan(&runsA)
	assert.Nil(t, err)

	err = pool.QueryRow(context.Background(),
		`SELECT COUNT(*) FROM connector_runs WHERE study_id = $1`,
		studyB).Scan(&runsB)
	assert.Nil(t, err)

	assert.Equal(t, 1, runsA, "Study A should have 1 connector_run record with 0 events written")
	assert.Equal(t, 1, runsB, "Study B should have 1 connector_run record")
}
