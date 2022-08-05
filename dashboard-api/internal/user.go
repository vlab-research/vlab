package studiesmanager

import (
	"context"
	"errors"
)

type UserRepository interface {
	CreateUser(ctx context.Context, userId string) (User, error)
}

type SaveCredentials interface {
	SaveCredentials(ctx context.Context, clientId string, clientSecret string) (User, error)
}

var ErrUserAlreadyExists = errors.New("User Already Exists")

//go:generate mockery --case=snake --outpkg=storagemocks --output=platform/storage/storagemocks --name=UserRepository

type User struct {
	Id string `json:"id"`
}
