package storage

import (
	"context"
	"database/sql"
	"errors"
	"testing"
	"time"

	"github.com/DATA-DOG/go-sqlmock"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/vlab-research/vlab/api/internal/types"
)

var (
	CurrentUserID = "auth0|61916c1dab79c900713936de"
	TestOrgID     = "fda19390-d1e7-4893-a13a-d14c88cc737b"
)

func Test_StudyRepository_GetStudyBySlug_StudyNotFoundError(t *testing.T) {
	studySlug := "example-study"

	db, sqlMock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherEqual))
	require.NoError(t, err)
	q := `
	SELECT id, name, created 
	FROM studies 
	WHERE slug = $1 AND (user_id = $2 OR org_id = $3)
	`
	sqlMock.ExpectQuery(q).
		WithArgs(studySlug, CurrentUserID, TestOrgID).
		WillReturnError(sql.ErrNoRows)

	repo := NewStudyRepository(db)

	_, err = repo.GetStudyBySlug(
		context.TODO(),
		studySlug,
		CurrentUserID,
		TestOrgID,
	)

	assert.NoError(t, sqlMock.ExpectationsWereMet())
	assert.ErrorIs(t, err, types.ErrStudyNotFound)
}

func Test_StudyRepository_GetStudyBySlug_UnexpectedError(t *testing.T) {
	studySlug := "example-study"

	db, sqlMock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherEqual))
	require.NoError(t, err)

	q := `
	SELECT id, name, created 
	FROM studies 
	WHERE slug = $1 AND (user_id = $2 OR org_id = $3)
	`
	sqlMock.ExpectQuery(q).
		WithArgs(studySlug, CurrentUserID, TestOrgID).
		WillReturnError(errors.New("unexpected-error"))

	repo := NewStudyRepository(db)

	_, err = repo.GetStudyBySlug(
		context.TODO(),
		studySlug,
		CurrentUserID,
		TestOrgID,
	)

	assert.NoError(t, sqlMock.ExpectationsWereMet())
	if assert.NotErrorIs(t, err, types.ErrStudyNotFound) {
		assert.Equal(t, errors.New("error trying to search a study with slug 'example-study' on the database: unexpected-error"), err)
	}
}

func Test_StudyRepository_GetStudyBySlug_Succeed(t *testing.T) {
	studySlug := "example-study"
	studyCreatedAt := time.Date(2020, time.November, 10, 23, 0, 0, 0, time.UTC)

	db, sqlMock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherEqual))
	require.NoError(t, err)

	rows := sqlMock.NewRows([]string{"id", "name", "created"}).
		AddRow("7261456a-77b7-4731-a499-629f9f49abe8", "Example Study", studyCreatedAt)
	q := `
	SELECT id, name, created 
	FROM studies 
	WHERE slug = $1 AND (user_id = $2 OR org_id = $3)
	`
	sqlMock.ExpectQuery(q).
		WithArgs(studySlug, CurrentUserID, TestOrgID).
		WillReturnRows(rows)

	repo := NewStudyRepository(db)

	study, err := repo.GetStudyBySlug(
		context.TODO(),
		studySlug,
		CurrentUserID,
		TestOrgID,
	)

	assert.NoError(t, sqlMock.ExpectationsWereMet())
	assert.NoError(t, err)
	expectedStudy := types.NewStudy("7261456a-77b7-4731-a499-629f9f49abe8", "Example Study", "example-study", 1605049200000)
	assert.Equal(t, expectedStudy, study)
}

func Test_StudyRepository_GetStudies_UnexpectedError_during_Query(t *testing.T) {
	offset := 0
	limit := 20

	db, sqlMock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherEqual))
	require.NoError(t, err)
	q := `
	SELECT id, name, slug, created 
	FROM studies 
	WHERE user_id = $3 OR org_id = $4 
	ORDER BY created DESC OFFSET $1 LIMIT $2
	`
	sqlMock.ExpectQuery(q).
		WithArgs(offset, limit, CurrentUserID, TestOrgID).
		WillReturnError(errors.New("unexpected-error"))

	repo := NewStudyRepository(db)

	_, err = repo.GetStudies(
		context.TODO(),
		offset,
		limit,
		CurrentUserID,
		TestOrgID,
	)

	assert.NoError(t, sqlMock.ExpectationsWereMet())
	assert.Equal(t, errors.New("(db.Query) error trying to get studies (offset: 0, limit: 20, userID: auth0|61916c1dab79c900713936de): unexpected-error"), err)
}

func Test_StudyRepository_GetStudies_UnexpectedError_during_Scan(t *testing.T) {
	offset := 0
	limit := 20

	db, sqlMock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherEqual))
	require.NoError(t, err)

	rows := sqlMock.NewRows([]string{"id", "name", "slug"}).
		AddRow("7261456a-77b7-4731-a499-629f9f49abe8", "Example Study", "example-study")

	q := `
	SELECT id, name, slug, created 
	FROM studies 
	WHERE user_id = $3 OR org_id = $4 
	ORDER BY created DESC OFFSET $1 LIMIT $2
	`
	sqlMock.ExpectQuery(q).
		WithArgs(offset, limit, CurrentUserID, TestOrgID).
		WillReturnRows(rows)

	repo := NewStudyRepository(db)

	_, err = repo.GetStudies(
		context.TODO(),
		offset,
		limit,
		CurrentUserID,
		TestOrgID,
	)

	assert.NoError(t, sqlMock.ExpectationsWereMet())
	assert.Equal(t, errors.New("(rows.Scan) error trying to get studies (offset: 0, limit: 20, userID: auth0|61916c1dab79c900713936de): sql: expected 3 destination arguments in Scan, not 4"), err)
}

func Test_StudyRepository_GetStudies_Succeed(t *testing.T) {
	offset := 0
	limit := 20
	studyID := "7261456a-77b7-4731-a499-629f9f49abe8"
	studyName := "Example Study"
	studySlug := "example-study"
	studyCreatedAt := time.Date(2020, time.November, 10, 23, 0, 0, 0, time.UTC)

	db, sqlMock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherEqual))
	require.NoError(t, err)

	rows := sqlMock.NewRows([]string{"id", "name", "slug", "created"}).
		AddRow(studyID, studyName, studySlug, studyCreatedAt)

	q := `
	SELECT id, name, slug, created 
	FROM studies 
	WHERE user_id = $3 OR org_id = $4 
	ORDER BY created DESC OFFSET $1 LIMIT $2
	`
	sqlMock.ExpectQuery(q).
		WithArgs(offset, limit, CurrentUserID, TestOrgID).
		WillReturnRows(rows)

	repo := NewStudyRepository(db)

	studies, err := repo.GetStudies(
		context.TODO(),
		offset,
		limit,
		CurrentUserID,
		TestOrgID,
	)

	assert.NoError(t, sqlMock.ExpectationsWereMet())
	assert.NoError(t, err)
	assert.Equal(t, []types.Study{types.NewStudy(studyID, studyName, studySlug, 1605049200000)}, studies)
}
