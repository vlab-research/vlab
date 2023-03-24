package storage

import (
	"context"
	"database/sql"
	"fmt"
	"strings"

	"github.com/vlab-research/vlab/dashboard-api/internal/types"
)

type UserRepository struct {
	db *sql.DB
}

func NewUserRepository(db *sql.DB) *UserRepository {
	return &UserRepository{
		db: db,
	}
}

func (r *UserRepository) CreateUser(ctx context.Context, userId string) (types.User, error) {
	_, err := r.db.Exec("INSERT INTO users (id) VALUES ($1)", userId)

	if err != nil {
		if strings.Contains(err.Error(), "(SQLSTATE 23505)") {
			return types.User{}, fmt.Errorf("%w: %s", types.ErrUserAlreadyExists, userId)
		}

		return types.User{}, fmt.Errorf("user with id '%s' cannot be created: %v", userId, err)
	}

	return types.User{
		Id: userId,
	}, nil
}
