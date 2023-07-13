package facebook

import (
	"net/http"
	"github.com/gin-gonic/gin"
	fb "github.com/huandu/facebook/v2"
	"github.com/vlab-research/vlab/api/internal/server/middleware/auth"
	"github.com/vlab-research/vlab/api/internal/storage"
	"github.com/vlab-research/vlab/api/internal/types"
)

type request struct {
	Code string `json:"code" binding:"required"`
}

type createResponse struct {
	Data types.Account `json:"data"`
}

// Takes a code generated from the Facebook Auth0 flow and and generates a set of credentials
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
			AuthType: "facebook", 
			Name:     "Facebook",
			ConnectedAccount: &types.FacebookConnectedAccount{
				Credentials: types.FacebookCredentials{
					AccessToken: token,
					ExpiresIn:   expire,
					TokenType:   "bearer",
				},
			},
		}
		// Stale Facebook credentials are deleted to avoid duplication
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
		err = a.SetConnectedAccount()
		if err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		ctx.JSON(http.StatusCreated, createResponse{Data: a})
	}
}
