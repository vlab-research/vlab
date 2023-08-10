package types

// QualtricsCredentials is used to unmarshal the credentials needed
// to integrate with a Qualtrics
// NOTE: This is an API interface that is depended on
// externally. Please take care when changing
type QualtricsCredentials struct {
	APIKey       string `json:"api_key"`
	ClientID     string `json:"client_id"`
	ClientSecret string `json:"client_secret"`
}
