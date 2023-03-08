package studies

import (
	"errors"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	studiesmanager "github.com/vlab-research/vlab/dashboard-api/internal"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/server/middleware/auth"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/storage"
)

type createRequest struct {
	StudyName string `json:"name"`
}

type createResponse struct {
	Data studiesmanager.Study `json:"data"`
}

// CreateHandler is a gin handler that is used to create
// a new Study object in the database
func CreateHandler(repositories storage.Repositories) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		var req, err = parseRequest(ctx)
		if err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		study, err := repositories.Study.CreateStudy(
			ctx,
			req.StudyName,
			auth.GetUserIdFrom(ctx),
		)

		if err != nil {
			switch {
			case errors.Is(err, studiesmanager.ErrStudyAlreadyExist):
				ctx.JSON(
					http.StatusConflict,
					gin.H{"error": "The name is already in use."},
				)
				return
			default:
				ctx.Status(http.StatusInternalServerError)
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
