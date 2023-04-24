package types

import (
	"context"
	"encoding/json"
	"errors"

	sourcetypes "github.com/vlab-research/vlab/inference/sources/types"
)

type AccountType string

// We currently Only Support a Limited amount of Accounts
// Through the API
const (
	TypeformAccount AccountType = "typeform"
	FlyAccount      AccountType = "fly"
	AlchemerAccount AccountType = "alchemer"
)

type AccountRepository interface {
	Create(ctx context.Context, a Account) error
	Delete(ctx context.Context, a Account) error
	List(ctx context.Context, offset, limit int, userID string) ([]Account, error)
}

var ErrAccountAlreadyExists = errors.New("Account Already Exists")
var ErrAccountDoesNotExists = errors.New("account does not exist")

// ConnectedAccount is used to enable the frontend to not need complex
// logic in order to determine if an account has been "connected".
// if this is null, then no account is connected
type ConnectedAccount interface {
	MarshalCredentials() (string, error)
}

type Account struct {
	UserID   string      `json:"userId"`
	AuthType string      `json:"authType" validate:"required"`
	Name     AccountType `json:"name" validate:"required"`
	// This is an interum structure to hold the credentials values
	// until it can be determined what kind of Connected Account
	// this is based on the name
	RawConnectedAccount json.RawMessage  `json:"connectedAccount"`
	ConnectedAccount    ConnectedAccount `json:"-"`
}

// SetRawConnectedAccount takes the connected account and
// sets it to RawConnectedAccount to be used in responses
func (a *Account) SetRawConnectedAccount() error {
	b, err := json.Marshal(a.ConnectedAccount)
	if err != nil {
		return err
	}
	a.RawConnectedAccount = b
	return nil
}

type FlyConnectedAccount struct {
	CreatedAt   int                        `json:"createdAt"`
	Credentials sourcetypes.FlyCredentials `json:"credentials" validate:"required"`
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
	CreatedAt   int                             `json:"createdAt"`
	Credentials sourcetypes.TypeformCredentials `json:"credentials" validate:"required"`
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

// FacebookConnectedAccount is used to connect Vlabs to a facebook ad account
type FacebookConnectedAccount struct {
	CreatedAt   int                 `json:"createdAt"`
	Credentials FacebookCredentials `json:"credentials" validate:"required"`
}

type FacebookCredentials struct {
	ExpiresIn   int    `json:"expires_in"`
	AccessToken string `json:"access_token"`
	TokenType   string `json:"token_type"`
}

// MarshalsCredentials is used to input data into the database
// as a JSONB field
func (f FacebookConnectedAccount) MarshalCredentials() (string, error) {
	b, err := json.Marshal(f.Credentials)
	if err != nil {
		return "", err
	}
	return string(b), nil
}

// AlchemerConnectedAccount is used to connect Vlabs to a facebook ad account
type AlchemerConnectedAccount struct {
	CreatedAt   int                       `json:"createdAt"`
	Credentials sourcetypes.AlchemerCreds `json:"credentials" validate:"required"`
}

// MarshalsCredentials is used to input data into the database
// as a JSONB field
func (a AlchemerConnectedAccount) MarshalCredentials() (string, error) {
	b, err := json.Marshal(a.Credentials)
	if err != nil {
		return "", err
	}
	return string(b), nil
}
