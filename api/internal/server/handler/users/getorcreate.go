package users

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/vlab-research/vlab/api/internal/server/middleware/auth"
	"github.com/vlab-research/vlab/api/internal/storage"
)

type response struct {
	Data interface{} `json:"data"`
}

// GetOrCreateHandler tries to create a user, if successful it will return the
// user with a status 201, if user already exists it will return the user with a
// status of 200
func GetOrCreateHandler(r storage.Repositories) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		user, err := r.User.Create(ctx, auth.GetUserIdFrom(ctx))
		if err != nil {
			ctx.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		// TODO: we should probably try and combine this into one call
		// when we get or create the user
		// however im not sure on how to join tables on an UPSERT
		orgIDs, orgErr := r.User.GetUserOrgIDs(ctx, auth.GetUserIdFrom(ctx))
		if orgErr != nil {
			// if there is an error collecting org ids we just return the user
			// without them
			ctx.JSON(http.StatusCreated, response{Data: user})
			return
		}
		user.Orgs = orgIDs
		ctx.JSON(http.StatusCreated, response{Data: user})
	}
}
