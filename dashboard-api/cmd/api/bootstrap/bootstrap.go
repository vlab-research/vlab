package bootstrap

import (
	"context"
	"database/sql"
	"fmt"

	_ "github.com/jackc/pgx/v4/stdlib"
	"github.com/kelseyhightower/envconfig"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/server"
	cockroachdb "github.com/vlab-research/vlab/dashboard-api/internal/platform/storage/cockroachdb"
)

func Run() error {
	var cfg config
	err := envconfig.Process("STUDIESMANAGER", &cfg)
	if err != nil {
		return fmt.Errorf("envconfig.Process: %w", err)
	}

	db, err := sql.Open("pgx", cfg.DbUri)
	if err != nil {
		return fmt.Errorf("sql.Open: %w", err)
	}
	if err := db.PingContext(context.Background()); err != nil {
		return fmt.Errorf("db.PingContext: %w", err)
	}

	studyRepository := cockroachdb.NewStudyRepository(db)

	srv := server.New(cfg.Host, cfg.Port, db, studyRepository)
	return srv.Run()
}

type config struct {
	Host  string `default:"localhost"`
	Port  uint   `default:"8080"`
	DbUri string `default:"postgresql://root@localhost:26257/vlab?sslmode=disable"`
}
