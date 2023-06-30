package accounts

import (
	"net/http"
	"github.com/gin-gonic/gin"
	"github.com/vlab-research/vlab/api/internal/helpers"
	"github.com/vlab-research/vlab/api/internal/server/middleware/auth"
	"github.com/vlab-research/vlab/api/internal/storage"
	"github.com/vlab-research/vlab/api/internal/types"
)

type listResponse struct {
	Data       []types.Account                `json:"data"`
	Pagination helpers.ListResponsePagination `json:"pagination"`
}

func ListHandler(r storage.Repositories) gin.HandlerFunc {
	return func(ctx *gin.Context) {

		p := helpers.NewPagination()
		err := p.ParseQueryParams(ctx)
		if err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		accType := ctx.DefaultQuery("type", "not set")
		accounts, err := r.Account.List(
			ctx,
			p.Cursor,
			p.Number,
			auth.GetUserIdFrom(ctx),
			accType,
		)

		if err != nil {
			ctx.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		var nextCursor *string
		if len(accounts) >= p.Number {
			nextCursor = p.CreateNextCursor()
		}

		ctx.JSON(http.StatusOK, listResponse{
			Data: accounts,
			Pagination: helpers.ListResponsePagination{
				NextCursor: nextCursor,
			},
		})
	}
}
