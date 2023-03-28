package types

import (
	"context"
	"errors"
)

type UserRepository interface {
	Create(ctx context.Context, userID string) (User, error)
	GetUserOrgIDs(ctx context.Context, userID string) ([]Org, error)
}

var ErrUserAlreadyExists = errors.New("User Already Exists")

type Org struct {
	ID   string `json:"id"`
	Name string `json:"name"`
}

type User struct {
	ID   string `json:"id"`
	Orgs []Org  `json:"orgs"`
}
