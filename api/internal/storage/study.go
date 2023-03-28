package storage

import (
	"context"
	"database/sql"
	"fmt"
	"strings"
	"time"

	"github.com/gosimple/slug"
	"github.com/vlab-research/vlab/api/internal/types"
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

// GetStudyBySlug fetches a study by using the slug
func (r *StudyRepository) GetStudyBySlug(
	ctx context.Context,
	slug, userID, orgID string,
) (types.Study, error) {
	var id, name string
	var created time.Time

	q := `
		SELECT id, name, created 
		FROM studies 
		WHERE slug = $1 AND (user_id = $2 OR org_id = $3)
		`

	row := r.db.QueryRow(
		q,
		slug,
		userID,
		orgID,
	)

	if err := row.Scan(&id, &name, &created); err != nil {
		if err == sql.ErrNoRows {
			return types.Study{}, fmt.Errorf(
				"%w: %s",
				types.ErrStudyNotFound,
				slug,
			)
		}

		return types.Study{}, fmt.Errorf(
			"error trying to search a study with slug '%s' on the database: %v",
			slug,
			err,
		)
	}

	return types.NewStudy(id, name, slug, created.UnixMilli()), nil
}

// GetStudies returns a paginated list of studies
// based on an offset and limit
func (r *StudyRepository) GetStudies(
	ctx context.Context,
	offset int, limit int,
	userID, orgID string,
) ([]types.Study, error) {
	studies := []types.Study{}

	q := `
	SELECT id, name, slug, created 
	FROM studies 
	WHERE user_id = $3 OR org_id = $4
	ORDER BY created DESC OFFSET $1 LIMIT $2
	`
	rows, err := r.db.Query(q, offset, limit, userID, orgID)
	if err != nil {
		return nil, fmt.Errorf("(db.Query) error trying to get studies (offset: %d, limit: %d, userID: %s): %v", offset, limit, userID, err)
	}

	defer rows.Close()

	for rows.Next() {
		var id, name, slug string
		var createdAt time.Time

		if err := rows.Scan(&id, &name, &slug, &createdAt); err != nil {
			return nil, fmt.Errorf("(rows.Scan) error trying to get studies (offset: %d, limit: %d, userID: %s): %v", offset, limit, userID, err)
		}

		study := types.NewStudy(id, name, slug, createdAt.UnixMilli())

		studies = append(studies, study)
	}

	return studies, nil
}

// CreateStudy used to do the row creation in the database for the study
// objects
func (r *StudyRepository) CreateStudy(
	ctx context.Context,
	name, userID, orgID string,
) (types.Study, error) {

	slug := slug.Make(name)
	q := `
		INSERT INTO studies (slug, name, user_id, org_id) 
		VALUES ($1, $2, $3, $4) RETURNING id,created
	`
	row := r.db.QueryRow(
		q,
		slug,
		name,
		userID,
		orgID,
	)

	var id string
	var created time.Time

	if err := row.Scan(&id, &created); err != nil {
		if strings.Contains(err.Error(), "violates unique constraint") {
			return types.Study{}, fmt.Errorf("%w: %s", types.ErrStudyAlreadyExist, slug)
		}
		return types.Study{}, fmt.Errorf("study (slug: %s, name: %s, userId: %s) cannot be created: %v", slug, name, userID, err)
	}
	return types.NewStudy(id, name, slug, created.UnixMilli()), nil
}
