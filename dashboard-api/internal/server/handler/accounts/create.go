package accounts

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/go-playground/validator/v10"
	studiesmanager "github.com/vlab-research/vlab/dashboard-api/internal"
	"github.com/vlab-research/vlab/dashboard-api/internal/server/middleware/auth"
	"github.com/vlab-research/vlab/dashboard-api/internal/storage"
)

// use a single instance , it caches struct info
var (
	validate *validator.Validate
)

type createResponse struct {
	Data studiesmanager.Account `json:"data"`
}

// CreateHandler is a gin handler that is used to create
// a new account object in the database
func CreateHandler(repositories storage.Repositories) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		b, err := ioutil.ReadAll(ctx.Request.Body)
		if err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		a, err := parsePayload(b)
		if err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		uid := auth.GetUserIdFrom(ctx)
		a.UserID = uid
		err = repositories.Account.Create(ctx, a)
		if err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		ctx.JSON(http.StatusCreated, createResponse{Data: a})
	}
}

// parsePayload is a simple parser to determine the type of account
// TODO: Potentially move this to the accounts file closer to the types
func parsePayload(b []byte) (a studiesmanager.Account, err error) {
	if err := json.Unmarshal(b, &a); err != nil {
		return a, err
	}

	switch a.Name {
	case studiesmanager.FlyAccount:
		a.ConnectedAccount = &studiesmanager.FlyConnectedAccount{}
	case studiesmanager.TypeformAccount:
		a.ConnectedAccount = &studiesmanager.TypeformConnectedAccount{}
	default:
		return a, fmt.Errorf("unknown account type %v", a.Name)
	}

	if err = json.Unmarshal(a.RawConnectedAccount, a.ConnectedAccount); err != nil {
		return a, err
	}

	// runs validation against required fields
	//TODO: make error messages more readable
	validate = validator.New()
	if err = validate.Struct(a); err != nil {
		return a, err
	}

	return a, nil
}
