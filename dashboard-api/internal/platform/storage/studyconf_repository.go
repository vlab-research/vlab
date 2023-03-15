package storage

import (
	"context"
	"database/sql"
	"fmt"

	"github.com/vlab-research/vlab/dashboard-api/internal/types"
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
