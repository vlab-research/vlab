package accounts

import (
	"encoding/json"
	"io/ioutil"
	"net/http"
	"github.com/gin-gonic/gin"
	"github.com/vlab-research/vlab/api/internal/server/middleware/auth"
	"github.com/vlab-research/vlab/api/internal/storage"
	"github.com/vlab-research/vlab/api/internal/types"
)

// Gin handler used to delete an account object in the db
// Name and authType are required in the body of the request due to the interface of the account resource
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
			case types.ErrAccountDoesNotExist:
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
