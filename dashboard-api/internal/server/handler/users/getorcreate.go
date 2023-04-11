package users

import (
	"errors"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/vlab-research/vlab/dashboard-api/internal/server/middleware/auth"
	"github.com/vlab-research/vlab/dashboard-api/internal/storage"
	"github.com/vlab-research/vlab/dashboard-api/internal/types"
)

type response struct {
	Data interface{} `json:"data"`
}

// GetOrCreateHandler tries to create a user, if successful it will return the
// user with a status 201, if user already exists it will return the user with a
// status of 200
func GetOrCreateHandler(repositories storage.Repositories) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		user, err := repositories.User.Create(ctx, auth.GetUserIdFrom(ctx))
		if err != nil {
			switch {
			// In the case of a user already existing we just return the user
			// with a status of 200
			case errors.Is(err, types.ErrUserAlreadyExists):
				ctx.JSON(http.StatusOK, response{Data: user})
				return
			default:
				ctx.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
		}

		ctx.JSON(http.StatusCreated, response{Data: user})
	}
}
