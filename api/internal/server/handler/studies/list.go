package studies

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/vlab-research/vlab/dashboard-api/internal/helpers"
	"github.com/vlab-research/vlab/dashboard-api/internal/server/middleware/auth"
	"github.com/vlab-research/vlab/dashboard-api/internal/storage"
	"github.com/vlab-research/vlab/dashboard-api/internal/types"
)

type listResponse struct {
	Data       []types.Study                  `json:"data"`
	Pagination helpers.ListResponsePagination `json:"pagination"`
}

func ListHandler(repositories storage.Repositories) gin.HandlerFunc {
	return func(ctx *gin.Context) {

		p := helpers.NewPagination()
		err := p.ParseQueryParams(ctx)
		if err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		studies, err := repositories.Study.GetStudies(
			ctx,
			p.Cursor,
			p.Number,
			auth.GetUserIdFrom(ctx),
		)
		if err != nil {
			ctx.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		var nextCursor *string
		if len(studies) >= p.Number {
			nextCursor = p.CreateNextCursor()
		}

		ctx.JSON(http.StatusOK, listResponse{
			Data: studies,
			Pagination: helpers.ListResponsePagination{
				NextCursor: nextCursor,
			},
		})
	}
}
