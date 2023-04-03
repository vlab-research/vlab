package config

import (
	"github.com/kelseyhightower/envconfig"
)

// Config is where all configuration is held for the applictaion
type Config struct {
	Host  string `envconfig:"API_HOST"`
	Port  uint   `envconfig:"API_PORT"`
	DB    string `envconfig:"PG_URL"`
	Auth0 struct {
		Domain   string `envconfig:"AUTH0_DOMAIN"`
		Audience string `envconfig:"AUTH0_AUDIENCE"`
	}
	Facebook struct {
		ClientID     string `envconfig:"FACEBOOK_CLIENT_ID"`
		ClientSecret string `envconfig:"FACEBOOK_CLIENT_SECRET"`
	}
}

// Setup processes the environment and returns an config
// struct to be used through the application
func Setup() (*Config, error) {
	var cfg Config
	err := envconfig.Process("", &cfg)
	if err != nil {
		return &cfg, err
	}

	return &cfg, nil
}
