package studiesmanager

import (
	"context"
	"errors"
)

type StudyRepository interface {
	GetStudyBySlug(ctx context.Context, slug string) (Study, error)
}

var ErrStudyNotFound = errors.New("Study not found")

//go:generate mockery --case=snake --outpkg=storagemocks --output=platform/storage/storagemocks --name=StudyRepository

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
