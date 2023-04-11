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

func (r *UserRepository) Create(ctx context.Context, userID string) (types.User, error) {
	_, err := r.db.Exec("INSERT INTO users (id) VALUES ($1)", userID)

	if err != nil {
		if strings.Contains(err.Error(), "(SQLSTATE 23505)") {
			return types.User{ID: userID}, types.ErrUserAlreadyExists
		}

		return types.User{}, fmt.Errorf("user with id '%s' cannot be created: %v", userID, err)
	}

	return types.User{
		ID: userID,
	}, nil
}
