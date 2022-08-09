package studiesmanager

import (
	"context"
	"errors"
	"time"
)

type UserRepository interface {
	CreateUser(ctx context.Context, userId string) (User, error)
}

type SaveCredentialsFly interface {
	SaveCredentialsFly(ctx context.Context, clientId string, nickname string) (User, error)
}

type GetCredentials interface {
	GetCredentials(ctx context.Context, clientId string) (Credentials, error)
}

var ErrUserAlreadyExists = errors.New("User Already Exists")

//go:generate mockery --case=snake --outpkg=storagemocks --output=platform/storage/storagemocks --name=UserRepository

type User struct {
	Id string `json:"id"`
}

type Credentials struct {
	Userid  string
	Entity  string
	Key     string
	Created time.Time
	Details string
}
