package accounts

import (
	"encoding/json"
	"io/ioutil"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/vlab-research/vlab/dashboard-api/internal/server/middleware/auth"
	"github.com/vlab-research/vlab/dashboard-api/internal/storage"
	"github.com/vlab-research/vlab/dashboard-api/internal/types"
)

// DeleteHandler is a gin handler that is used to delete
// a account object in the database. Because of the nature of the resource
// we require to send a body with some data through, including
// authType and name of account
func DeleteHandler(r storage.Repositories) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		b, err := ioutil.ReadAll(ctx.Request.Body)
		if err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		var a types.Account
		err = json.Unmarshal(b, &a)
		if err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		uid := auth.GetUserIdFrom(ctx)
		a.UserID = uid

		err = r.Account.Delete(ctx, a)
		if err != nil {
			var status int
			switch err {
			case types.ErrAccountDoesNotExists:
				status = http.StatusNotFound
			default:
				status = http.StatusBadRequest
			}
			ctx.JSON(status, gin.H{"error": err.Error()})
			return
		}
		ctx.Status(http.StatusNoContent)
	}
}