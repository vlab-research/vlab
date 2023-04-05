package types

import (
	"context"
	"errors"
)

type StudyRepository interface {
	GetStudyBySlug(ctx context.Context, slug, userId string) (Study, error)
	GetStudies(ctx context.Context, offset int, limit int, userId string) ([]Study, error)
	CreateStudy(ctx context.Context, name, userId string) (Study, error)
}

var ErrStudyNotFound = errors.New("Study not found")
var ErrStudyAlreadyExist = errors.New("Study already exist")

type Study struct {
	Id        string `json:"id"`
	Name      string `json:"name"`
	Slug      string `json:"slug"`
	CreatedAt int64  `json:"createdAt"`
}

func NewStudy(id, name, slug string, createdAt int64) Study {
	return Study{
		Id:        id,
		Name:      name,
		Slug:      slug,
		CreatedAt: createdAt,
	}
}
