package storage

import (
	"context"
	"database/sql"
	"log"

	_ "github.com/jackc/pgx/v4/stdlib"
	studiesmanager "github.com/vlab-research/vlab/dashboard-api/internal"
	"github.com/vlab-research/vlab/dashboard-api/internal/types"
)

type Repositories struct {
	Db            *sql.DB
	Study         studiesmanager.StudyRepository
	StudySegments studiesmanager.StudySegmentsRepository
	User          studiesmanager.UserRepository
	Account       studiesmanager.AccountRepository
	StudyConf     types.StudyConfRepository
}

func InitializeRepositories(dbURI string) Repositories {
	db, err := sql.Open("pgx", dbURI)
	if err != nil {
		log.Fatalf("sql.Open: %v", err)
	}
	if err := db.PingContext(context.Background()); err != nil {
		log.Fatalf("db.PingContext: %v", err)
	}

	return Repositories{
		Db:            db,
		Study:         NewStudyRepository(db),
		StudySegments: NewStudySegmentsRepository(db),
		User:          NewUserRepository(db),
		Account:       NewAccountRepository(db),
		StudyConf:     NewStudyConfRepository(db),
	}
}
