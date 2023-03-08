package storage

import (
	"context"
	"database/sql"
	"fmt"
	"strings"

	studiesmanager "github.com/vlab-research/vlab/dashboard-api/internal"
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
	a studiesmanager.Account,
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

func handleCreateError(e error, a studiesmanager.Account) error {
	if strings.Contains(e.Error(), "(SQLSTATE 23505)") {
		return fmt.Errorf("%w: %s", studiesmanager.ErrAccountAlreadyExists, a.Name)
	}
	return fmt.Errorf(
		"account with name '%s' cannot be created: %v",
		a.Name,
		e,
	)
}
