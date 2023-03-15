package storage

import (
	"context"
	"testing"

	"github.com/DATA-DOG/go-sqlmock"
	"github.com/stretchr/testify/require"
	"github.com/vlab-research/vlab/dashboard-api/internal/types"
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
