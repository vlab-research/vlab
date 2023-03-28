package storage

import (
	"context"
	"database/sql"
	"fmt"

	"github.com/vlab-research/vlab/api/internal/types"
)

type StudyConfRepository struct {
	db *sql.DB
}

func NewStudyConfRepository(db *sql.DB) *StudyConfRepository {
	return &StudyConfRepository{
		db: db,
	}
}

// Create creates a new study_conf object in the database
// NOTE: Study Configs have no unique identifiers and this function
// will not have logic to check for duplicates
func (r *StudyConfRepository) Create(
	ctx context.Context,
	sc types.DatabaseStudyConf,
) error {

	q := "INSERT INTO study_confs (study_id, conf_type, conf) VALUES ($1, $2, $3)"
	_, err := r.db.ExecContext(
		ctx,
		q,
		sc.StudyID,
		sc.ConfType,
		sc.Conf,
	)

	if err != nil {
		return fmt.Errorf(
			"failed creating config of type %s for study: %v", sc.ConfType, err.Error(),
		)
	}

	return nil
}

// GetConfsByStudy will return all the latest unique confs that are attached to
// a study
func (r *StudyConfRepository) GetByStudySlug(
	ctx context.Context,
	slug, userID string,
) ([]*types.DatabaseStudyConf, error) {

	var dscs []*types.DatabaseStudyConf

	// We get the latest of each study conf by study slug so we join the studies
	// table to handle the filtering
	q := `
	SELECT DISTINCT ON(conf_type) sc.study_id, sc.conf_type, sc.conf, sc.created
	FROM study_confs sc
	JOIN studies s on s.id = sc.study_id
	WHERE s.slug = $1 AND s.user_id=$2
	ORDER BY conf_type, created DESC;
	`

	rows, err := r.db.QueryContext(ctx, q, slug, userID)
	if err != nil {
		return dscs, err
	}

	for rows.Next() {
		d := new(types.DatabaseStudyConf)
		err := rows.Scan(&d.StudyID, &d.ConfType, &d.Conf, &d.Created)
		if err != nil {
			return dscs, err
		}
		dscs = append(dscs, d)
	}

	return dscs, nil
}
