package types

import (
	"context"
	"encoding/json"
	"errors"
	sourcetypes "github.com/vlab-research/vlab/inference/sources/types"
)

type AccountType string

const (
	// The API currently only supports these 3 account types
	TypeformAccount AccountType = "typeform"
	FlyAccount      AccountType = "fly"
	AlchemerAccount AccountType = "alchemer"
)

type AccountRepository interface {
	Create(ctx context.Context, a Account) error
	Delete(ctx context.Context, a Account) error
	List(ctx context.Context, offset, limit int, userID, accType string) ([]Account, error)
}

var ErrAccountAlreadyExists = errors.New("Account already exists")
var ErrAccountDoesNotExist = errors.New("Account does not exist")

// connected account is used as a concept 
// to avoid complex logic on the frontend
// if null then the account is considered not yet connected
type ConnectedAccount interface {
	MarshalCredentials() (string, error)
}

type Account struct {
	UserID   string `json:"userId"`
	Name     string `json:"name" validate:"required"`
	AuthType AccountType `json:"authType" validate:"required"`
	// This is an interim structure to hold the credential values 
	// until it can be determined what type of connected account it is based on its authType
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

// MarshalsCredentials is used to input data into the database as a JSONB field
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

// MarshalsCredentials is used to input data into the database as a JSONB field
func (t TypeformConnectedAccount) MarshalCredentials() (string, error) {
	b, err := json.Marshal(t.Credentials)
	if err != nil {
		return "", err
	}
	return string(b), nil
}

// FacebookConnectedAccount is used to connect Virtual Lab to a Facebook ad account
type FacebookConnectedAccount struct {
	CreatedAt   int                 `json:"createdAt"`
	Credentials FacebookCredentials `json:"credentials" validate:"required"`
}

type FacebookCredentials struct {
	ExpiresIn   int    `json:"expires_in"`
	AccessToken string `json:"access_token"`
	TokenType   string `json:"token_type"`
}

// MarshalsCredentials is used to input data into the database as a JSONB field
func (f FacebookConnectedAccount) MarshalCredentials() (string, error) {
	b, err := json.Marshal(f.Credentials)
	if err != nil {
		return "", err
	}
	return string(b), nil
}

// AlchemerConnectedAccount is used to connect Virtual Lab to a Facebook ad account
type AlchemerConnectedAccount struct {
	CreatedAt   int                       `json:"createdAt"`
	Credentials sourcetypes.AlchemerCreds `json:"credentials" validate:"required"`
}

// MarshalsCredentials is used to input data into the database as a JSONB field
func (a AlchemerConnectedAccount) MarshalCredentials() (string, error) {
	b, err := json.Marshal(a.Credentials)
	if err != nil {
		return "", err
	}
	return string(b), nil
}
