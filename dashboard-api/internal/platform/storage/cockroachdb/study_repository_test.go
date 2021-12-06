package cockroachdb

import (
	"context"
	"database/sql"
	"errors"
	"testing"
	"time"

	"github.com/DATA-DOG/go-sqlmock"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	studiesmanager "github.com/vlab-research/vlab/dashboard-api/internal"
)

func Test_StudyRepository_GetStudyBySlug_StudyNotFoundError(t *testing.T) {
	studySlug := "example-study"

	db, sqlMock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherEqual))
	require.NoError(t, err)

	sqlMock.ExpectQuery(
		"SELECT id, name, created FROM studies WHERE slug = $1").
		WithArgs(studySlug).
		WillReturnError(sql.ErrNoRows)

	repo := NewStudyRepository(db)

	_, err = repo.GetStudyBySlug(context.Background(), studySlug)

	assert.NoError(t, sqlMock.ExpectationsWereMet())
	assert.ErrorIs(t, err, studiesmanager.ErrStudyNotFound)
}

func Test_StudyRepository_GetStudyBySlug_UnexpectedError(t *testing.T) {
	studySlug := "example-study"

	db, sqlMock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherEqual))
	require.NoError(t, err)

	sqlMock.ExpectQuery(
		"SELECT id, name, created FROM studies WHERE slug = $1").
		WithArgs(studySlug).
		WillReturnError(errors.New("unexpected-error"))

	repo := NewStudyRepository(db)

	_, err = repo.GetStudyBySlug(context.Background(), studySlug)

	assert.NoError(t, sqlMock.ExpectationsWereMet())
	if assert.NotErrorIs(t, err, studiesmanager.ErrStudyNotFound) {
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
	sqlMock.ExpectQuery(
		"SELECT id, name, created FROM studies WHERE slug = $1").
		WithArgs(studySlug).
		WillReturnRows(rows)

	repo := NewStudyRepository(db)

	study, err := repo.GetStudyBySlug(context.Background(), studySlug)

	assert.NoError(t, sqlMock.ExpectationsWereMet())
	assert.NoError(t, err)
	expectedStudy := studiesmanager.NewStudy("7261456a-77b7-4731-a499-629f9f49abe8", "Example Study", "example-study", 1605049200000)
	assert.Equal(t, expectedStudy, study)
}

func Test_StudyRepository_GetStudies_UnexpectedError_during_Query(t *testing.T) {
	offset := 0
	limit := 20

	db, sqlMock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherEqual))
	require.NoError(t, err)

	sqlMock.ExpectQuery(
		"SELECT id, name, slug, created FROM studies ORDER BY created DESC OFFSET $1 LIMIT $2").
		WithArgs(offset, limit).
		WillReturnError(errors.New("unexpected-error"))

	repo := NewStudyRepository(db)

	_, err = repo.GetStudies(context.Background(), offset, limit)

	assert.NoError(t, sqlMock.ExpectationsWereMet())
	assert.Equal(t, errors.New("(db.Query) error trying to get studies (offset: 0, limit: 20): unexpected-error"), err)
}

func Test_StudyRepository_GetStudies_UnexpectedError_during_Scan(t *testing.T) {
	offset := 0
	limit := 20

	db, sqlMock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherEqual))
	require.NoError(t, err)

	rows := sqlMock.NewRows([]string{"id", "name", "slug"}).
		AddRow("7261456a-77b7-4731-a499-629f9f49abe8", "Example Study", "example-study")

	sqlMock.ExpectQuery(
		"SELECT id, name, slug, created FROM studies ORDER BY created DESC OFFSET $1 LIMIT $2").
		WithArgs(offset, limit).
		WillReturnRows(rows)

	repo := NewStudyRepository(db)

	_, err = repo.GetStudies(context.Background(), offset, limit)

	assert.NoError(t, sqlMock.ExpectationsWereMet())
	assert.Equal(t, errors.New("(rows.Scan) error trying to get studies (offset: 0, limit: 20): sql: expected 3 destination arguments in Scan, not 4"), err)
}

func Test_StudyRepository_GetStudies_Succeed(t *testing.T) {
	offset := 0
	limit := 20
	studyId := "7261456a-77b7-4731-a499-629f9f49abe8"
	studyName := "Example Study"
	studySlug := "example-study"
	studyCreatedAt := time.Date(2020, time.November, 10, 23, 0, 0, 0, time.UTC)

	db, sqlMock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherEqual))
	require.NoError(t, err)

	rows := sqlMock.NewRows([]string{"id", "name", "slug", "created"}).
		AddRow(studyId, studyName, studySlug, studyCreatedAt)

	sqlMock.ExpectQuery(
		"SELECT id, name, slug, created FROM studies ORDER BY created DESC OFFSET $1 LIMIT $2").
		WithArgs(offset, limit).
		WillReturnRows(rows)

	repo := NewStudyRepository(db)

	studies, err := repo.GetStudies(context.Background(), offset, limit)

	assert.NoError(t, sqlMock.ExpectationsWereMet())
	assert.NoError(t, err)
	assert.Equal(t, []studiesmanager.Study{studiesmanager.NewStudy(studyId, studyName, studySlug, 1605049200000)}, studies)
}
