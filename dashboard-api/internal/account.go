package studiesmanager

import (
	"context"
	"encoding/json"
	"errors"
	"time"

	flytypes "github.com/vlab-research/vlab/inference/sources/fly/types"
)

type AccountType string

// We currently Only Support a Limited amount of Accounts
// Through the API
const (
	TypeformAccount AccountType = "Typeform"
	FlyAccount      AccountType = "Fly"
)

type AccountRepository interface {
	Create(ctx context.Context, a Account) error
}

var ErrAccountAlreadyExists = errors.New("Account Already Exists")

//go:generate mockery --case=snake --outpkg=storagemocks
//--output=platform/storage/storagemocks --name=AccountRepository

// ConnectedAccount is used to enable the frontend to not need complex
// logic in order to determine if an account has been "connected".
// if this is null, then no account is connected
type ConnectedAccount interface {
	MarshalCredentials() (string, error)
}

type Account struct {
	ID       string      `json:"id" `
	UserID   string      `json:"userId"`
	AuthType string      `json:"authType" validate:"required"`
	Name     AccountType `json:"name" validate:"required"`
	// This is an interum structure to hold the credentials values
	// until it can be determined what kind of Connected Account
	// this is based on the name
	RawConnectedAccount json.RawMessage  `json:"connectedAccount"`
	ConnectedAccount    ConnectedAccount `json:"-"`
}

type FlyConnectedAccount struct {
	CreatedAt   time.Time               `json:"createdAt"`
	Credentials flytypes.FlyCredentials `json:"credentials" validate:"required"`
}

// MarshalsCredentials is used to input data into the database
// as a JSONB field
func (f FlyConnectedAccount) MarshalCredentials() (string, error) {
	b, err := json.Marshal(f.Credentials)
	if err != nil {
		return "", err
	}
	return string(b), nil
}

type TypeformConnectedAccount struct {
	CreatedAt   time.Time           `json:"createdAt"`
	Credentials TypeformCredentials `json:"credentials" validate:"required"`
}

type TypeformCredentials struct {
	Key string `json:"key" validate:"required"`
}

// MarshalsCredentials is used to input data into the database
// as a JSONB field
func (t TypeformConnectedAccount) MarshalCredentials() (string, error) {
	b, err := json.Marshal(t.Credentials)
	if err != nil {
		return "", err
	}
	return string(b), nil
}
