package facebook

import (
	"net/http"

	"github.com/gin-gonic/gin"
	fb "github.com/huandu/facebook/v2"
	"github.com/vlab-research/vlab/dashboard-api/internal/server/middleware/auth"
	"github.com/vlab-research/vlab/dashboard-api/internal/storage"
	"github.com/vlab-research/vlab/dashboard-api/internal/types"
)

type request struct {
	Code string `json:"code" binding:"required"`
}

type createResponse struct {
	Data types.Account `json:"data"`
}

// GenerateToken takes a code that is generated from the facebook
// Auth0 flow where a user gives permission for our app
// and generates a set of credentials for use by Vlabs
func GenerateToken(a *fb.App, r storage.Repositories) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		req := &request{}
		if err := ctx.ShouldBindJSON(req); err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		token, expire, _, err := a.ParseCodeInfo(req.Code, "")
		if err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		a := types.Account{
			UserID:   auth.GetUserIdFrom(ctx),
			AuthType: "bearer",
			Name:     "facebook",
			ConnectedAccount: &types.FacebookConnectedAccount{
				Credentials: types.FacebookCredentials{
					AccessToken: token,
					ExpiresIn:   expire,
					TokenType:   "bearer",
				},
			},
		}
		// We first delete the old facebook credentials
		// due to the problem of duplicating credential keys
		err = r.Account.Delete(ctx, a)
		if err != nil && err != types.ErrAccountDoesNotExists {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		err = r.Account.Create(ctx, a)
		if err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		err = a.SetRawConnectedAccount()
		if err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		ctx.JSON(http.StatusCreated, createResponse{Data: a})
	}
}
