package segmentsprogress

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/vlab-research/vlab/dashboard-api/internal/storage"

	"github.com/vlab-research/vlab/dashboard-api/internal/server/middleware/auth"
)

// ListHandler will return a list of segment progresses
// If the study does not exist  or the user does not have access
// to the study it will return an empty response
func ListHandler(r storage.Repositories) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		var req struct {
			Slug string `uri:"slug" binding:"required"`
		}
		if err := ctx.ShouldBindUri(&req); err != nil {
			ctx.Status(http.StatusBadRequest)
			return
		}

		sp, err := r.StudySegments.GetByStudySlug(ctx, req.Slug, auth.GetUserIdFrom(ctx))
		if err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		ctx.JSON(http.StatusOK, gin.H{
			"data": sp,
		})
	}
}
