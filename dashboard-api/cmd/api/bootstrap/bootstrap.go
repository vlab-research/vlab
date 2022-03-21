package bootstrap

import (
	"fmt"

	_ "github.com/jackc/pgx/v4/stdlib"
	"github.com/kelseyhightower/envconfig"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/server"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/server/middleware/auth"
	storage "github.com/vlab-research/vlab/dashboard-api/internal/platform/storage"
)

func Run() error {
	var cfg config
	err := envconfig.Process("", &cfg)
	if err != nil {
		return fmt.Errorf("envconfig.Process: %w", err)
	}

	dbUri := fmt.Sprintf("postgresql://%s:%s@%s:%d/%s?sslmode=%s", cfg.DbUser, cfg.DbPassword, cfg.DbHost, cfg.DbPort, cfg.DbName, cfg.SslMode)
	srv := server.New(
		cfg.Host,
		cfg.Port,
		storage.InitializeRepositories(dbUri),
		auth.EnsureValidTokenMiddleware(cfg.Auth0.Domain, cfg.Auth0.Audience),
		cfg.Auth0.Domain,
	)
	return srv.Run()
}

type config struct {
	Host       string `envconfig:"API_HOST"`
	Port       uint   `envconfig:"API_PORT"`
	SslMode    string `envconfig:"DATABASE_SSL"`
	DbName     string `envconfig:"DATABASE_NAME"`
	DbHost     string `envconfig:"DATABASE_HOST"`
	DbPort     uint   `envconfig:"DATABASE_PORT"`
	DbUser     string `envconfig:"DATABASE_USER"`
	DbPassword string `envconfig:"DATABASE_PASSWORD"`
	Auth0      struct {
		Domain   string `envconfig:"AUTH0_DOMAIN"`
		Audience string `envconfig:"AUTH0_AUDIENCE"`
	}
}
