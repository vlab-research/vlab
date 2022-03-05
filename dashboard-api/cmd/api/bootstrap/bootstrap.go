package bootstrap

import (
	"fmt"

	_ "github.com/jackc/pgx/v4/stdlib"
	"github.com/kelseyhightower/envconfig"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/server"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/server/middleware/auth"
	storage "github.com/vlab-research/vlab/dashboard-api/internal/platform/storage"
)

type config struct {
	Host       string `default:"localhost" envconfig:"API_HOST"`
	Port       uint   `default:"8080" envconfig:"API_PORT"`
	DbName     string `default:"vlab" envconfig:"DATABASE_NAME"`
	DbHost     string `default:"cockroachdb" envconfig:"DATABASE_HOST"`
	DbPort     uint   `default:"26257" envconfig:"DATABASE_PORT"`
	DbUser     string `default:"root" envconfig:"DATABASE_USER"`
	DbPassword string `default:"" envconfig:"DATABASE_PASSWORD"`
	Auth0      struct {
		Domain   string `default:"https://vlab-dev.us.auth0.com/"`
		Audience string `default:"https://api-dev.vlab/"`
	}
}

func GetConfig() (config, error) {
	var cfg config
	err := envconfig.Process("", &cfg)
	if err != nil {
		return config{}, fmt.Errorf("envconfig.Process: %w", err)
	}

	return cfg, nil
}

func Run() error {
	cfg, err := GetConfig()
	if err != nil {
		return err
	}

	dbUri := fmt.Sprintf("postgresql://%s:%s@%s:%d/%s?sslmode=disable", cfg.DbUser, cfg.DbPassword, cfg.DbHost, cfg.DbPort, cfg.DbName)
	srv := server.New(
		cfg.Host,
		cfg.Port,
		storage.InitializeRepositories(dbUri),
		auth.EnsureValidTokenMiddleware(cfg.Auth0.Domain, cfg.Auth0.Audience),
		cfg.Auth0.Domain,
	)
	return srv.Run()
}
