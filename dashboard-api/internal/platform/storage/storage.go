package storage

import (
	"context"
	"database/sql"
	"log"
	"time"

	_ "github.com/jackc/pgx/v4/stdlib"
	studiesmanager "github.com/vlab-research/vlab/dashboard-api/internal"
)

type Repositories struct {
	Db                      *sql.DB
	Study                   studiesmanager.StudyRepository
	StudySegments           studiesmanager.StudySegmentsRepository
	User                    studiesmanager.UserRepository
	SaveCredentialsFly      studiesmanager.SaveCredentialsFly
	GetCredentials          studiesmanager.GetCredentials
	SaveCredentialsTypeform studiesmanager.SaveCredentialsTypeform
}

type Credentials struct {
	Userid  string
	Entity  string
	Key     string
	Created time.Time
	Details string
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
		Db:                      db,
		Study:                   NewStudyRepository(db),
		StudySegments:           NewStudySegmentsRepository(db),
		User:                    NewUserRepository(db),
		SaveCredentialsFly:      NewSaveCredentialsFly(db),
		SaveCredentialsTypeform: NewSaveCredentialsTypeform(db),
		GetCredentials:          NewGetCredentials(db),
	}
}
