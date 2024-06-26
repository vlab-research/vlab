package studyconf

import (
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/vlab-research/vlab/api/internal/server/middleware/auth"
	"github.com/vlab-research/vlab/api/internal/storage"
	"github.com/vlab-research/vlab/api/internal/types"
)

type readResponse struct {
	Data types.StudyConf `json:"data"`
}

// ReadHandler is a gin handler used to retrieve a studies configuration
func ReadHandler(r storage.Repositories) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		var req struct {
			Slug string `uri:"slug" binding:"required"`
			Org  string `uri:"org" binding:"required"`
		}
		if err := ctx.ShouldBindUri(&req); err != nil {
			ctx.Status(http.StatusBadRequest)
			return
		}

		dscs, err := r.StudyConf.GetByStudySlug(ctx, req.Slug, auth.GetUserIdFrom(ctx))
		if err != nil {
			handleError(ctx, err)
			return
		}

		sc := types.StudyConf{}
		err = sc.TransformFromDatabase(dscs)
		if err != nil {
			handleError(ctx, err)
			return
		}

		ctx.JSON(http.StatusOK, readResponse{Data: sc})
	}
}

func handleError(ctx *gin.Context, err error) {
	switch {
	default:
		msg := fmt.Sprintf("an unexpected error occured - %v", err.Error())
		ctx.JSON(http.StatusBadRequest, gin.H{"error": msg})
		return
	}
}
