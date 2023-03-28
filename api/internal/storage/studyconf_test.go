package storage

import (
	"context"
	"testing"
	"time"

	"github.com/DATA-DOG/go-sqlmock"
	"github.com/stretchr/testify/require"
	"github.com/vlab-research/vlab/api/internal/types"
)

func Test_StudyConfRepository_Create_StudyConf(t *testing.T) {
	assert := require.New(t)

	t.Run("with valid config", func(t *testing.T) {
		sc := types.DatabaseStudyConf{
			StudyID:  "1234",
			ConfType: "general",
			Conf:     []byte(`{"foo": "bar"}`),
		}

		db, sqlMock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherEqual))

		assert.NoError(err)
		q := "INSERT INTO study_confs (study_id, conf_type, conf) VALUES ($1, $2, $3)"
		sqlMock.ExpectExec(q).
			WithArgs(sc.StudyID, sc.ConfType, sc.Conf).
			WillReturnResult(sqlmock.NewResult(1, 1))

		repo := NewStudyConfRepository(db)

		err = repo.Create(context.Background(), sc)

		assert.NoError(err)
		assert.NoError(sqlMock.ExpectationsWereMet())
	})
}

func Test_StudyConfRepository_GetByStudyID(t *testing.T) {
	assert := require.New(t)

	t.Run("with valid studyID", func(t *testing.T) {
		slug := "test-study"
		sc := types.DatabaseStudyConf{
			StudyID:  "1234",
			ConfType: "general",
			Conf:     []byte(`{"foo": "bar"}`),
			Created:  time.Date(2020, time.November, 10, 23, 0, 0, 0, time.UTC),
		}

		db, sqlMock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherEqual))

		assert.NoError(err)
		q := `
			SELECT DISTINCT ON(conf_type) sc.study_id, sc.conf_type, sc.conf, sc.created 
			FROM study_confs sc
			JOIN studies s on s.id = sc.study_id
			WHERE s.slug = $1 AND s.user_id=$2
			ORDER BY conf_type, created DESC;
			`

		columns := []string{"study_id", "conf_type", "conf", "created"}
		mockRows := sqlmock.NewRows(columns).
			AddRow(
				"1234",
				"general",
				[]byte(`{"foo": "bar"}`),
				time.Date(2020, time.November, 10, 23, 0, 0, 0, time.UTC),
			)
		sqlMock.ExpectQuery(q).
			WithArgs(slug, "1234").
			WillReturnRows(mockRows)

		repo := NewStudyConfRepository(db)

		dscs, err := repo.GetByStudySlug(context.Background(), slug, "1234")

		assert.NoError(err)
		assert.Equal(sc, *dscs[0])
		assert.NoError(sqlMock.ExpectationsWereMet())
	})
}
