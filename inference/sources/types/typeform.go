package types

// TypeformCredentials is used to unmarshal the credentials needed
// to integrate with typeform
// NOTE: This is an API interface that is depended on
// externally. Please take care when changing
type TypeformCredentials struct {
	Key string `json:"key" validate:"required"`
}
