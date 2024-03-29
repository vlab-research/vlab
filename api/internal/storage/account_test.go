package storage

import (
	"context"
	"testing"

	"github.com/DATA-DOG/go-sqlmock"
	"github.com/stretchr/testify/require"

	"github.com/vlab-research/vlab/api/internal/types"
	sourcetypes "github.com/vlab-research/vlab/inference/sources/types"
)

func Test_AccountRepository_Create_Account(t *testing.T) {
	assert := require.New(t)

	t.Run("with valid fly credentials", func(t *testing.T) {
		a := types.Account{
			UserID:   "auth0|61916c1dab79c900713936de",
			Name:     "fly123",
			AuthType: "fly",
			ConnectedAccount: types.FlyConnectedAccount{
				CreatedAt: 0,
				Credentials: sourcetypes.FlyCredentials{
					APIKey: "supersecret",
				},
			},
		}
		expecetdCredentials := "{\"api_key\":\"supersecret\"}"

		db, sqlMock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherEqual))

		assert.NoError(err)
		q := "INSERT INTO credentials (user_id, entity, key, details) VALUES ($1, $2, $3, $4)"
		sqlMock.ExpectExec(q).
			WithArgs(a.UserID, a.Name, a.AuthType, expecetdCredentials).
			WillReturnResult(sqlmock.NewResult(1, 1))

		repo := NewAccountRepository(db)

		err = repo.Create(context.Background(), a)

		assert.NoError(err)
		assert.NoError(sqlMock.ExpectationsWereMet())
	})
}

func Test_AccountRepository_Delete_Account(t *testing.T) {
	assert := require.New(t)

	t.Run("deletes valid account", func(t *testing.T) {
		a := types.Account{
			UserID:   "auth0|61916c1dab79c900713936de",
			Name:     "fly123",
			AuthType: "fly",
		}

		db, sqlMock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherEqual))
		assert.NoError(err)
		q := `
		DELETE FROM credentials 
		WHERE user_id = $1
		AND entity = $2 
		AND key = $3
		`
		sqlMock.ExpectExec(q).
			WithArgs(a.UserID, a.Name, a.AuthType).
			WillReturnResult(sqlmock.NewResult(1, 1))

		repo := NewAccountRepository(db)

		err = repo.Delete(context.Background(), a)

		assert.NoError(err)
		assert.NoError(sqlMock.ExpectationsWereMet())
	})
}
