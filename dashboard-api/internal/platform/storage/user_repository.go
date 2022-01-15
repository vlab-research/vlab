package storage

import (
	"context"
	"database/sql"
	"fmt"

	studiesmanager "github.com/vlab-research/vlab/dashboard-api/internal"
)

type UserRepository struct {
	db *sql.DB
}

func NewUserRepository(db *sql.DB) *UserRepository {
	return &UserRepository{
		db: db,
	}
}

func (r *UserRepository) CreateUser(ctx context.Context, userId string) (studiesmanager.User, error) {
	_, err := r.db.Exec("INSERT INTO users (id) VALUES ($1)", userId)

	if err != nil {
		if err.Error() == "ERROR: duplicate key value violates unique constraint \"primary\" (SQLSTATE 23505)" {
			return studiesmanager.User{}, fmt.Errorf("%w: %s", studiesmanager.ErrUserAlreadyExists, userId)
		}

		return studiesmanager.User{}, fmt.Errorf("user with id '%s' cannot be created: %v", userId, err)
	}

	return studiesmanager.User{
		Id: userId,
	}, nil
}
