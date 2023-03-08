package storage

import (
	"context"
	"database/sql"
	"fmt"
	"strings"
	"time"

	"github.com/gosimple/slug"
	studiesmanager "github.com/vlab-research/vlab/dashboard-api/internal"
)

type StudyRepository struct {
	db *sql.DB
}

// NewStudyRepository returns a new instance of the Study Repository object
// to manage calls to the database
func NewStudyRepository(db *sql.DB) *StudyRepository {
	return &StudyRepository{
		db: db,
	}
}

func (r *StudyRepository) GetStudyBySlug(
	ctx context.Context,
	slug, userId string,
) (studiesmanager.Study, error) {
	var id, name string
	var created time.Time

	row := r.db.QueryRow(
		"SELECT id, name, created FROM studies WHERE slug = $1 AND user_id = $2",
		slug,
		userId,
	)

	if err := row.Scan(&id, &name, &created); err != nil {
		if err == sql.ErrNoRows {
			return studiesmanager.Study{}, fmt.Errorf(
				"%w: %s",
				studiesmanager.ErrStudyNotFound,
				slug,
			)
		}

		return studiesmanager.Study{}, fmt.Errorf(
			"error trying to search a study with slug '%s' on the database: %v",
			slug,
			err,
		)
	}

	return studiesmanager.NewStudy(id, name, slug, created.UnixMilli()), nil
}

func (r *StudyRepository) GetStudies(ctx context.Context, offset int, limit int, userId string) ([]studiesmanager.Study, error) {
	studies := []studiesmanager.Study{}

	rows, err := r.db.Query("SELECT id, name, slug, created FROM studies WHERE user_id = $3 ORDER BY created DESC OFFSET $1 LIMIT $2", offset, limit, userId)
	if err != nil {
		return nil, fmt.Errorf("(db.Query) error trying to get studies (offset: %d, limit: %d, userId: %s): %v", offset, limit, userId, err)
	}

	defer rows.Close()

	for rows.Next() {
		var id, name, slug string
		var createdAt time.Time

		if err := rows.Scan(&id, &name, &slug, &createdAt); err != nil {
			return nil, fmt.Errorf("(rows.Scan) error trying to get studies (offset: %d, limit: %d, userId: %s): %v", offset, limit, userId, err)
		}

		study := studiesmanager.NewStudy(id, name, slug, createdAt.UnixMilli())

		studies = append(studies, study)
	}

	return studies, nil
}

// CreateStudy used to do the row creation in the database for the study
// objects
func (r *StudyRepository) CreateStudy(
	ctx context.Context,
	name, userId string,
) (studiesmanager.Study, error) {

	slug := slug.Make(name)

	row := r.db.QueryRow(
		"INSERT INTO studies (slug, name, user_id) VALUES ($1, $2, $3) RETURNING id,created",
		slug,
		name,
		userId,
	)

	var id string
	var created time.Time

	if err := row.Scan(&id, &created); err != nil {
		if strings.Contains(err.Error(), "violates unique constraint") {
			return studiesmanager.Study{}, fmt.Errorf("%w: %s", studiesmanager.ErrStudyAlreadyExist, slug)
		}

		return studiesmanager.Study{}, fmt.Errorf("study (slug: %s, name: %s, userId: %s) cannot be created: %v", slug, name, userId, err)

	}

	return studiesmanager.NewStudy(id, name, slug, created.UnixMilli()), nil
}
