package storage

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"
	"github.com/vlab-research/vlab/api/internal/types"
)

type AccountRepository struct {
	db *sql.DB
}

func NewAccountRepository(db *sql.DB) *AccountRepository {
	return &AccountRepository{
		db: db,
	}
}

// Creates a new account object in the database

// Accounts map to the credentials table in the database in the following way:

// authType -> entity (this is used as the "Source")
// ConnectedAccount.Credentials -> details
// Name -> key
// UserId -> user_id

// user_id, name i.e key need to be unique
func (r *AccountRepository) Create(
	ctx context.Context,
	a types.Account,
) error {

	c, err := a.ConnectedAccount.MarshalCredentials()
	if err != nil {
		return handleCreateError(err, a)
	}

	q := "INSERT INTO credentials (user_id, entity, key, details) VALUES ($1, $2, $3, $4)"
	_, err = r.db.ExecContext(
		ctx,
		q,
		a.UserID,
		a.AuthType,
		a.Name,
		c,
	)

	if err != nil {
		return handleCreateError(err, a)
	}

	return nil
}

// Deletes a credential based on three fields user_id, entity and key (unique)
func (r *AccountRepository) Delete(
	ctx context.Context,
	a types.Account,
) error {

	q := `
		DELETE FROM credentials 
		WHERE user_id = $1
		AND entity = $2 
		AND key = $3
		`
	rows, err := r.db.ExecContext(
		ctx,
		q,
		a.UserID,
		a.AuthType,
		a.Name,
	)

	if err != nil {
		return errors.New("Failed to delete credential")
	}

	rowsAffected, err := rows.RowsAffected()

	if rowsAffected == 0 {
		return types.ErrAccountDoesNotExist
	}

	return err
}

func handleCreateError(e error, a types.Account) error {
	if strings.Contains(e.Error(), "(SQLSTATE 23505)") {

		return fmt.Errorf("%w: %s", types.ErrAccountAlreadyExists, a.AuthType)
	}
	return fmt.Errorf(
		"A '%s' account with name '%s' already exists",
		a.Name,
		a.AuthType,
	)
}

// List is used to pull credentials from the database and map them to an account
func (r *AccountRepository) List(
	ctx context.Context,
	offset, limit int,
	userId, accType string,
) ([]types.Account, error) {
	accounts := []types.Account{}

	q := `
		SELECT user_id, entity, key, details, created
		FROM credentials 
		WHERE user_id = $3 
		`
	args := []any{offset, limit, userId}
	if accType != "not set" {
		args = append(args, accType)
		q = fmt.Sprintf("%s%s\n", q, "AND entity = $4")
	}
	q = fmt.Sprintf("%s%s", q, `ORDER BY created DESC OFFSET $1 LIMIT $2`)
	rows, err := r.db.Query(q, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	for rows.Next() {
		var userID, entity, key string
		var created time.Time
		var details []byte
		if err := rows.Scan(&userID, &entity, &key, &details, &created); err != nil {
			return nil, err
		}
		var authType = types.AccountType(entity)

		accounts = append(accounts, types.Account{
			Name:     key,
			UserID:   userID,
			AuthType: authType,
			Account: []byte(fmt.Sprintf(
				`{"createdAt": "%s", "credentials": %s}`,
				created,
				details,
			)),
		})
	}

	return accounts, nil
}
