package storage

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"

	studiesmanager "github.com/vlab-research/vlab/dashboard-api/internal"
)

type UserRepository struct {
	db *sql.DB
}

func NewUserRepository(db *sql.DB) *UserRepository {
	return &UserRepository{
		db: db,
	}
}

func NewSaveCredentialsFly(db *sql.DB) *UserRepository {
	return &UserRepository{
		db: db,
	}
}

func NewGetCredentials(db *sql.DB) *UserRepository {
	return &UserRepository{
		db: db,
	}
}

func (r *UserRepository) CreateUser(ctx context.Context, userId string) (studiesmanager.User, error) {
	_, err := r.db.Exec("INSERT INTO users (id) VALUES ($1)", userId)

	if err != nil {
		if err.Error() == "ERROR: duplicate key value violates unique constraint \"primary\" (SQLSTATE 23505)" {
			return studiesmanager.User{}, fmt.Errorf("%w: %s", studiesmanager.ErrUserAlreadyExists, userId)
		}

		return studiesmanager.User{}, fmt.Errorf("user with id '%s' cannot be created: %v", userId, err)
	}

	return studiesmanager.User{
		Id: userId,
	}, nil
}

func (r *UserRepository) SaveCredentialsFly(ctx context.Context, clientId string, nickname string) (studiesmanager.User, error) {

	entity := "entity_fake"
	key := "key123"
	details := json.RawMessage(`{"first_name": "` + nickname + `"}`)

	_, err := r.db.Exec("INSERT INTO credentials (user_id, entity, key, details, rowid) VALUES ($1, $2, $3, $4, $5)", clientId, entity, key, details, 4)

	if err != nil {
		if err.Error() == "ERROR: duplicate key value violates unique constraint \"primary\" (SQLSTATE 23505)" {
			return studiesmanager.User{}, fmt.Errorf("%w: %s", studiesmanager.ErrUserAlreadyExists, clientId)
		}

		return studiesmanager.User{}, fmt.Errorf("user with id '%s' cannot be created: %v", clientId, err)
	}

	return studiesmanager.User{
		Id: clientId,
	}, nil
}

func (r *UserRepository) SaveCredentialsTypeform(ctx context.Context, clientId string, nickname string) (studiesmanager.User, error) {
	fmt.Println("Logic...")
	return studiesmanager.User{
		Id: clientId,
	}, nil
}

func (r *UserRepository) GetCredentials(ctx context.Context, clientId string) (studiesmanager.Credentials, error) {

	row := r.db.QueryRow("SELECT * FROM credentials WHERE user_id = $1", clientId)

	c := &studiesmanager.Credentials{}

	if err := row.Scan(&c.Userid, &c.Entity, &c.Key, &c.Created, &c.Details); err != nil {
		return studiesmanager.Credentials{}, fmt.Errorf("user with id '%s' not exists: %v", clientId, err)
	}

	return studiesmanager.Credentials{
		Userid:  c.Userid,
		Entity:  c.Entity,
		Key:     c.Key,
		Created: c.Created,
		Details: c.Details,
	}, nil

}
