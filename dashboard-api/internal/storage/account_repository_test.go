package storage

import (
	"context"
	"testing"
	"time"

	"github.com/DATA-DOG/go-sqlmock"
	"github.com/stretchr/testify/require"

	studiesmanager "github.com/vlab-research/vlab/dashboard-api/internal"
	flytypes "github.com/vlab-research/vlab/inference/sources/fly/types"
)

func Test_AccountRepository_Create_Account(t *testing.T) {
	assert := require.New(t)

	t.Run("with valid fly credentials", func(t *testing.T) {
		a := studiesmanager.Account{
			UserID:   "auth0|61916c1dab79c900713936de",
			Name:     "Fly",
			AuthType: "token",
			ConnectedAccount: studiesmanager.FlyConnectedAccount{
				CreatedAt: time.Date(2020, time.November, 10, 23, 0, 0, 0, time.UTC),
				Credentials: flytypes.FlyCredentials{
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