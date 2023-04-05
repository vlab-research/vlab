package studies

import (
	"errors"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/vlab-research/vlab/dashboard-api/internal/server/middleware/auth"
	"github.com/vlab-research/vlab/dashboard-api/internal/storage"
	"github.com/vlab-research/vlab/dashboard-api/internal/types"
)

type readResponse struct {
	Data types.Study `json:"data"`
}

func ReadHandler(repositories storage.Repositories) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		var req struct {
			Slug string `uri:"slug" binding:"required"`
		}
		if err := ctx.ShouldBindUri(&req); err != nil {
			ctx.Status(http.StatusInternalServerError)
			return
		}

		study, err := repositories.Study.GetStudyBySlug(ctx, req.Slug, auth.GetUserIdFrom(ctx))

		if err != nil {
			switch {
			case errors.Is(err, types.ErrStudyNotFound):
				ctx.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
				return

			default:
				ctx.Status(http.StatusInternalServerError)
				return
			}
		}

		ctx.JSON(http.StatusOK, readResponse{Data: study})
	}
}
