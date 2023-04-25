package types

// AlchemerCreds is used to unmarshal the credentials needed
// to integrate with a Alchemer
// NOTE: This is an API interface that is depended on
// externally. Please take care when changing
type AlchemerCreds struct {
	ApiToken       string `json:"api_token" validate:"required"`
	ApiTokenSecret string `json:"api_token_secret" validate:"required"`
}
