package cockroachdb

import (
	"context"
	"database/sql"
	"fmt"
	"time"

	studiesmanager "github.com/vlab-research/vlab/dashboard-api/internal"
)

type StudyRepository struct {
	db *sql.DB
}

func NewStudyRepository(db *sql.DB) *StudyRepository {
	return &StudyRepository{
		db: db,
	}
}

func (r *StudyRepository) GetStudyBySlug(ctx context.Context, slug string) (studiesmanager.Study, error) {
	var id, name string
	var created time.Time

	row := r.db.QueryRow("SELECT id, name, created FROM studies WHERE slug = $1", slug)

	if err := row.Scan(&id, &name, &created); err != nil {
		if err == sql.ErrNoRows {
			return studiesmanager.Study{}, fmt.Errorf("%w: %s", studiesmanager.ErrStudyNotFound, slug)
		}

		return studiesmanager.Study{}, fmt.Errorf("error trying to search a study with slug '%s' on the database: %v", slug, err)
	}

	return studiesmanager.NewStudy(id, name, slug, created.UnixMilli()), nil
}
