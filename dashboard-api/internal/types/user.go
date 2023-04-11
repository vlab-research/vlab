package types

import (
	"context"
	"errors"
)

type UserRepository interface {
	Create(ctx context.Context, userID string) (User, error)
}

var ErrUserAlreadyExists = errors.New("User Already Exists")

type User struct {
	ID string `json:"id"`
}
