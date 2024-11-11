package accounts

import (
	"encoding/json"
	"fmt"
	"github.com/gin-gonic/gin"
	"github.com/go-playground/validator/v10"
	"github.com/vlab-research/vlab/api/internal/server/middleware/auth"
	"github.com/vlab-research/vlab/api/internal/storage"
	"github.com/vlab-research/vlab/api/internal/types"
	"io/ioutil"
	"net/http"
)

var (
	// Uses a single instance and caches struct info
	validate *validator.Validate
)

type createResponse struct {
	Data types.Account `json:"data"`
}

// Gin handler used to create a new account object in the db
func CreateHandler(r storage.Repositories) gin.HandlerFunc {
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

		// Stale credentials are deleted to avoid duplicating credential keys
		err = r.Account.Delete(ctx, a)
		if err != nil && err != types.ErrAccountDoesNotExist {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		err = r.Account.Create(ctx, a)
		if err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		ctx.JSON(http.StatusCreated, createResponse{Data: a})
	}
}

// parsePayload() is a simple parser to determine account type
func parsePayload(b []byte) (a types.Account, err error) {
	if err := json.Unmarshal(b, &a); err != nil {
		return a, err
	}

	// TODO: move this to account.go closer to types

	switch a.AuthType {
	case types.FlyAccount:
		a.ConnectedAccount = &types.FlyConnectedAccount{}
	case types.TypeformAccount:
		a.ConnectedAccount = &types.TypeformConnectedAccount{}
	case types.AlchemerAccount:
		a.ConnectedAccount = &types.AlchemerConnectedAccount{}
	case types.FacebookAccount:
		a.ConnectedAccount = &types.FacebookConnectedAccount{}
	case types.VlabApiKeyAccount:
		a.ConnectedAccount = &types.VlabApiKeyConnectedAccount{}
	default:
		return a, fmt.Errorf("%v is an unknown account type", a.AuthType)
	}

	if err = json.Unmarshal(a.Account, a.ConnectedAccount); err != nil {
		return a, err
	}

	// Runs validation against required fields
	validate = validator.New()
	if err = validate.Struct(a); err != nil {
		return a, err
	}

	return a, nil
}
