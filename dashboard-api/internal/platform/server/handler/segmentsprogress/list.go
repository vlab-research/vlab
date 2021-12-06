package segmentsprogress

import (
	"errors"
	"net/http"

	"github.com/gin-gonic/gin"
	studiesmanager "github.com/vlab-research/vlab/dashboard-api/internal"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/storage"
)

func ListHandler(repositories storage.Repositories) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		var req struct {
			Slug string `uri:"slug" binding:"required"`
		}
		if err := ctx.ShouldBindUri(&req); err != nil {
			ctx.Status(http.StatusInternalServerError)
			return
		}

		study, err := repositories.Study.GetStudyBySlug(ctx, req.Slug)
		if err != nil {
			switch {
			case errors.Is(err, studiesmanager.ErrStudyNotFound):
				ctx.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
				return

			default:
				ctx.Status(http.StatusInternalServerError)
				return
			}
		}

		allTimeSegmentsProgress, err := repositories.StudySegments.GetAllTimeSegmentsProgress(ctx, study.Id)
		if err != nil {
			ctx.Status(http.StatusInternalServerError)
			return
		}

		ctx.JSON(http.StatusOK, gin.H{
			"data": allTimeSegmentsProgress,
		})
	}
}
