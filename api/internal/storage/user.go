package storage

import (
	"context"
	"database/sql"
	"fmt"

	"github.com/vlab-research/vlab/api/internal/types"
)

type UserRepository struct {
	db *sql.DB
}

func NewUserRepository(db *sql.DB) *UserRepository {
	return &UserRepository{
		db: db,
	}
}

func (r *UserRepository) Create(ctx context.Context, userID string) (types.User, error) {
	q := `
		WITH u AS (
			UPSERT INTO users (id)
			VALUES ($1)
			RETURNING id
		),	
		o AS (
			/*we have to use insert as upsert is only valid on primary keys*/
			INSERT INTO orgs (name)
			VALUES ($1)
			ON CONFLICT (name)
			DO UPDATE SET name = excluded.name
			RETURNING name, id AS org_id
		),
		ol AS (
			/*we have to use insert as upsert is only valid on primary keys*/
			INSERT INTO orgs_lookup (user_id, org_id)
			VALUES ((SELECT id FROM u), (SELECT org_id FROM o))
			ON CONFLICT (user_id, org_id)
			DO UPDATE SET 
				user_id = excluded.user_id,
				org_id = excluded.org_id
			RETURNING user_id
		)
		SELECT id FROM  u;
	`
	row := r.db.QueryRowContext(ctx, q, userID)

	var id string

	if err := row.Scan(&id); err != nil {
		return types.User{}, fmt.Errorf("user with id '%s' cannot be created: %v", userID, err)
	}

	return types.User{
		ID: id,
	}, nil
}

// GetUserOrgID returns a users org id based on their user id
func (r *UserRepository) GetUserOrgIDs(
	ctx context.Context,
	userID string,
) ([]types.Org, error) {
	var orgs []types.Org

	q := `
		SELECT o.id, o.name FROM orgs o
		JOIN orgs_lookup ol ON o.id = ol.org_id 
		WHERE ol.user_id = $1;
		`
	rows, err := r.db.QueryContext(ctx, q, userID)
	if err != nil {
		return orgs, fmt.Errorf("error fetching orgs: %v", err)
	}
	defer rows.Close()

	for rows.Next() {
		var id, name sql.NullString
		if err := rows.Scan(&id, &name); err != nil {
			return orgs, fmt.Errorf("could not fetch users org id: %v", err)
		}
		orgs = append(orgs, types.Org{Name: name.String, ID: id.String})
	}

	return orgs, nil
}
