package storage

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/vlab-research/vlab/dashboard-api/internal/types"
)

type AccountRepository struct {
	db *sql.DB
}

func NewAccountRepository(db *sql.DB) *AccountRepository {
	return &AccountRepository{
		db: db,
	}
}

// Create creates a new account object in the database
//
// Accounts Map to the Credentials table in the database in the following way:
//
// Name -> entity (This is used as the "Source")
// ConnectedAccount.Credentials -> details
// AuthType -> key
// UserId -> user_id
//
// user_id, entity, key need to be unique, therefore currently
// we will not allow more than one instance of an account Type
// i.e You can only connect one Fly Instance
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
		a.Name,
		a.AuthType,
		c,
	)

	if err != nil {
		return handleCreateError(err, a)
	}

	return nil
}

// Delete will delete a credential based on its three unique
// fields user_id, entity and key
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
		a.Name,
		a.AuthType,
	)

	if err != nil {
		return errors.New("failed to delete credential")
	}

	rowsAffected, err := rows.RowsAffected()

	if rowsAffected == 0 {
		return types.ErrAccountDoesNotExists
	}

	return err
}

func handleCreateError(e error, a types.Account) error {
	if strings.Contains(e.Error(), "(SQLSTATE 23505)") {
		return fmt.Errorf("%w: %s", types.ErrAccountAlreadyExists, a.Name)
	}
	return fmt.Errorf(
		"account with name '%s' cannot be created: %v",
		a.Name,
		e,
	)
}

// List is used to pull credentials from the database
// and map them to an account
func (r *AccountRepository) List(
	ctx context.Context,
	offset, limit int,
	userId string,
) ([]types.Account, error) {
	accounts := []types.Account{}

	q := `
		SELECT user_id, entity, key, details, created
		FROM credentials 
		WHERE user_id = $3 
		ORDER BY created DESC 
		OFFSET $1 LIMIT $2
		`
	rows, err := r.db.Query(q, offset, limit, userId)
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
		var name = types.AccountType(entity)

		accounts = append(accounts, types.Account{
			Name:     name,
			UserID:   userID,
			AuthType: key,
			RawConnectedAccount: []byte(fmt.Sprintf(
				`{"createdAt": "%s", "credentials": %s}`,
				created,
				details,
			)),
		})
	}

	return accounts, nil
}
