package types

import (
	"context"
	"errors"
)

type UserRepository interface {
	CreateUser(ctx context.Context, userId string) (User, error)
}

var ErrUserAlreadyExists = errors.New("User Already Exists")

type User struct {
	Id string `json:"id"`
}
