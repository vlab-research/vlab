package storage

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

func (r *StudyRepository) GetStudies(ctx context.Context, offset int, limit int) ([]studiesmanager.Study, error) {
	studies := []studiesmanager.Study{}

	rows, err := r.db.Query("SELECT id, name, slug, created FROM studies ORDER BY created DESC OFFSET $1 LIMIT $2", offset, limit)
	if err != nil {
		return nil, fmt.Errorf("(db.Query) error trying to get studies (offset: %d, limit: %d): %v", offset, limit, err)
	}

	defer rows.Close()

	for rows.Next() {
		var id, name, slug string
		var createdAt time.Time

		if err := rows.Scan(&id, &name, &slug, &createdAt); err != nil {
			return nil, fmt.Errorf("(rows.Scan) error trying to get studies (offset: %d, limit: %d): %v", offset, limit, err)
		}

		study := studiesmanager.NewStudy(id, name, slug, createdAt.UnixMilli())

		studies = append(studies, study)
	}

	return studies, nil
}
