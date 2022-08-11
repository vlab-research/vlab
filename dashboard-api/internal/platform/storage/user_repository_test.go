package storage

import (
	"context"
	"encoding/json"
	"errors"
	"testing"

	"github.com/DATA-DOG/go-sqlmock"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func Test_UserRepository_SaveCredentials_UnexpectedError_during_Query(t *testing.T) {
	clientId := "auth0|61916c1dab79c900713936d"
	nickname := "juancarrillodev"
	entity := "entity_fake"
	key := "key123"
	details := json.RawMessage(`{"first_name": "` + nickname + `"}`)

	db, sqlMock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherEqual))
	require.NoError(t, err)

	sqlMock.ExpectExec(
		"INSERT INTO credentials (user_id, entity, key, details, rowid) VALUES ($1, $2, $3, $4, $5)").
		WithArgs(clientId, entity, key, details, 4).
		WillReturnError(errors.New("unexpected-error"))

	repo := NewSaveCredentialsFly(db)

	_, err = repo.SaveCredentialsFly(context.Background(), clientId, nickname)

	assert.NoError(t, sqlMock.ExpectationsWereMet())
	assert.Equal(t, errors.New("user with id 'auth0|61916c1dab79c900713936d' cannot be created: unexpected-error"), err)
}

func Test_UserRepository_GetCredentials_UnexpectedError_during_Query(t *testing.T) {
	userId := "auth0|47016c1dab79c900713937fa"

	db, sqlMock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherEqual))
	require.NoError(t, err)

	sqlMock.ExpectQuery(
		"SELECT * FROM credentials WHERE user_id = $1").
		WithArgs(userId).
		WillReturnError(errors.New("unexpected-error"))

	repo := NewGetCredentials(db)

	_, err = repo.GetCredentials(context.Background(), userId)

	assert.Equal(t, errors.New("user with id 'auth0|47016c1dab79c900713937fa' not exists: unexpected-error"), err)
}
