package types

import (
	"context"
	"errors"
)

type StudyRepository interface {
	GetStudyBySlug(ctx context.Context, slug, userID, orgID string) (Study, error)
	GetStudies(
		ctx context.Context,
		offset int, limit int,
		userID, orgID string,
	) ([]Study, error)
	CreateStudy(ctx context.Context, name, userID, orgID string) (Study, error)
}

var ErrStudyNotFound = errors.New("Study not found")
var ErrStudyAlreadyExist = errors.New("Study already exist")

type Study struct {
	ID        string `json:"id"`
	Name      string `json:"name"`
	Slug      string `json:"slug"`
	CreatedAt int64  `json:"createdAt"`
}

func NewStudy(id, name, slug string, createdAt int64) Study {
	return Study{
		ID:        id,
		Name:      name,
		Slug:      slug,
		CreatedAt: createdAt,
	}
}
