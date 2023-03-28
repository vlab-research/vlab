package studies

import (
	"errors"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/vlab-research/vlab/api/internal/server/middleware/auth"
	"github.com/vlab-research/vlab/api/internal/storage"
	"github.com/vlab-research/vlab/api/internal/types"
)

type createRequest struct {
	StudyName string `json:"name"`
}

type createResponse struct {
	Data types.Study `json:"data"`
}

// CreateHandler is a gin handler that is used to create
// a new Study object in the database
func CreateHandler(r storage.Repositories) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		var uri struct {
			Org string `uri:"org" binding:"required"`
		}
		if err := ctx.ShouldBindUri(&uri); err != nil {
			ctx.Status(http.StatusInternalServerError)
			return
		}
		var req, err = parseRequest(ctx)
		if err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		study, err := r.Study.CreateStudy(
			ctx,
			req.StudyName,
			auth.GetUserIdFrom(ctx),
			uri.Org,
		)

		if err != nil {
			switch {
			case errors.Is(err, types.ErrStudyAlreadyExist):
				ctx.JSON(
					http.StatusConflict,
					gin.H{"error": "The name is already in use."},
				)
				return
			default:
				ctx.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
		}
		ctx.JSON(http.StatusCreated, createResponse{Data: study})
	}
}

func parseRequest(ctx *gin.Context) (createRequest, error) {
	var req createRequest
	if err := ctx.ShouldBindJSON(&req); err != nil {
		return createRequest{}, err
	}

	if strings.TrimSpace(req.StudyName) == "" {
		return createRequest{}, errors.New("The name cannot be empty.")
	}

	if len(req.StudyName) > 300 {
		return createRequest{}, errors.New("The name cannot be larger than 300 characters.")
	}

	return req, nil
}
