package types

// QualtricsCredentials is used to unmarshal the credentials needed
// to integrate with a Qualtrics
// NOTE: This is an API interface that is depended on
// externally. Please take care when changing
type QualtricsCredentials struct {
	ClientID     string `json:"client_id" validate:"required"`
	ClientSecret string `json:"client_secret" validate:"required"`
}
