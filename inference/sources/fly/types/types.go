package types

// FlyCredentials is used to unmarshal the credentials needed
// to integrate with a Fly instance
// NOTE: This is an API interface that is depended on
// externally. Please take care when changing
type FlyCredentials struct {
	APIKey string `json:"api_key" validate:"required"`
}
