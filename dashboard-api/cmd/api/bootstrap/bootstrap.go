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
	err := envconfig.Process("STUDIESMANAGER", &cfg)
	if err != nil {
		return fmt.Errorf("envconfig.Process: %w", err)
	}

	srv := server.New(
		cfg.Host,
		cfg.Port,
		storage.InitializeRepositories(cfg.DbUri),
		auth.EnsureValidTokenMiddleware(cfg.Auth0.Domain, cfg.Auth0.Audience),
		cfg.Auth0.Domain,
	)
	return srv.Run()
}

type config struct {
	Host  string `default:"localhost"`
	Port  uint   `default:"8080"`
	DbUri string `default:"postgresql://root@localhost:26257/vlab?sslmode=disable"`
	Auth0 struct {
		Domain   string `default:"https://vlab-dev.us.auth0.com/"`
		Audience string `default:"https://api-dev.vlab/"`
	}
}
