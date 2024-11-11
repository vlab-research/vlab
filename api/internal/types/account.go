package types

import (
	"context"
	"encoding/json"
	"errors"
	sourcetypes "github.com/vlab-research/vlab/inference/sources/types"
)

type AccountType string

const (
	TypeformAccount   AccountType = "typeform"
	FlyAccount        AccountType = "fly"
	AlchemerAccount   AccountType = "alchemer"
	FacebookAccount   AccountType = "facebook"
	VlabApiKeyAccount AccountType = "api_key"
)

type AccountRepository interface {
	Create(ctx context.Context, a Account) error
	Delete(ctx context.Context, a Account) error
	List(ctx context.Context, offset, limit int, userID, accType string) ([]Account, error)
}

var ErrAccountAlreadyExists = errors.New("Account already exists")
var ErrAccountDoesNotExist = errors.New("Account not found")

type Account struct {
	UserID   string      `json:"userId"`
	Name     string      `json:"name" validate:"required"`
	AuthType AccountType `json:"authType" validate:"required"`
	// Interim structure to hold credential values until account type can be determined
	Account          json.RawMessage  `json:"connectedAccount"`
	ConnectedAccount ConnectedAccount `json:"-"`
}

// Takes the account and sets it to a connected account
func (a *Account) SetConnectedAccount() error {
	b, err := json.Marshal(a.Account)
	if err != nil {
		return err
	}
	a.Account = b
	return nil
}

// Used as a concept to avoid complex logic on the frontend
// If null then the account is considered not yet connected
type ConnectedAccount interface {
	MarshalCredentials() (string, error)
}

type FlyConnectedAccount struct {
	CreatedAt   int                        `json:"createdAt"`
	Credentials sourcetypes.FlyCredentials `json:"credentials" validate:"required"`
}

// Used to input data into the database as a JSONB field
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

// Used to input data into the database as a JSONB field
func (t TypeformConnectedAccount) MarshalCredentials() (string, error) {
	b, err := json.Marshal(t.Credentials)
	if err != nil {
		return "", err
	}
	return string(b), nil
}

type FacebookCredentials struct {
	ExpiresIn   int    `json:"expires_in"`
	AccessToken string `json:"access_token"`
	TokenType   string `json:"token_type"`
}

// Used to connect Virtual Lab to a Facebook ad account
type FacebookConnectedAccount struct {
	CreatedAt   int                 `json:"createdAt"`
	Credentials FacebookCredentials `json:"credentials" validate:"required"`
}

// Used to input data into the database as a JSONB field
func (f FacebookConnectedAccount) MarshalCredentials() (string, error) {
	b, err := json.Marshal(f.Credentials)
	if err != nil {
		return "", err
	}
	return string(b), nil
}

// Used to connect Virtual Lab to a Alchemer account
type AlchemerConnectedAccount struct {
	CreatedAt   int                       `json:"createdAt"`
	Credentials sourcetypes.AlchemerCreds `json:"credentials" validate:"required"`
}

// Used to input data into the database as a JSONB field
func (a AlchemerConnectedAccount) MarshalCredentials() (string, error) {
	b, err := json.Marshal(a.Credentials)
	if err != nil {
		return "", err
	}
	return string(b), nil
}

type VlabApiKeyCreds struct {
	Token string `json:"token" validate:"required"`
	ID    string `json:"id" validate:"required"`
}

// Used to generate Virtual Lab API Keys
type VlabApiKeyConnectedAccount struct {
	CreatedAt   int             `json:"createdAt"`
	Credentials VlabApiKeyCreds `json:"credentials" validate:"required"`
}

// Used to input data into the database as a JSONB field
func (a VlabApiKeyConnectedAccount) MarshalCredentials() (string, error) {
	b, err := json.Marshal(a.Credentials)
	if err != nil {
		return "", err
	}
	return string(b), nil
}
