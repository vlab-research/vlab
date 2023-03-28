package studies

import (
	"errors"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/vlab-research/vlab/api/internal/server/middleware/auth"
	"github.com/vlab-research/vlab/api/internal/storage"
	"github.com/vlab-research/vlab/api/internal/types"
)

type readResponse struct {
	Data types.Study `json:"data"`
}

func ReadHandler(r storage.Repositories) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		var req struct {
			Slug string `uri:"slug" binding:"required"`
			Org  string `uri:"org" binding:"required"`
		}
		if err := ctx.ShouldBindUri(&req); err != nil {
			ctx.Status(http.StatusInternalServerError)
			return
		}

		study, err := r.Study.GetStudyBySlug(
			ctx,
			req.Slug,
			auth.GetUserIdFrom(ctx),
			req.Org,
		)

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
