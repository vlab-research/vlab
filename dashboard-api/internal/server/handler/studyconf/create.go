package studyconf

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/go-playground/validator/v10"
	"github.com/hashicorp/go-multierror"
	"github.com/vlab-research/vlab/dashboard-api/internal/server/middleware/auth"
	"github.com/vlab-research/vlab/dashboard-api/internal/storage"
	"github.com/vlab-research/vlab/dashboard-api/internal/types"
)

// use a single instance , it caches struct info
var (
	validate *validator.Validate
)

type createResponse struct {
	Data types.StudyConf `json:"data"`
}

// CreateHandler is a gin handler that is used to create
// the relevant study configuration objects in the database
func CreateHandler(r storage.Repositories) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		var uriparams struct {
			Slug string `uri:"slug" binding:"required"`
		}
		if err := ctx.ShouldBindUri(&uriparams); err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		uid := auth.GetUserIdFrom(ctx)
		//fetch the related study
		study, err := r.Study.GetStudyBySlug(ctx, uriparams.Slug, uid)
		if err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{
				"error": fmt.Sprintf(
					"failed finding study with identifier %s",
					uriparams.Slug,
				),
			})
			return
		}

		b, err := ioutil.ReadAll(ctx.Request.Body)
		if err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		sc, err := parsePayload(b)
		sc.UserID = uid
		sc.StudyID = study.Id

		// We need to transform the data into what the database accepts
		databaseStudyConfs, err := sc.TransformForDatabase()
		if err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		for _, dsc := range databaseStudyConfs {
			e := r.StudyConf.Create(ctx, dsc)
			if e != nil {
				err = multierror.Append(err, e)
			}
		}
		if err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		ctx.JSON(http.StatusCreated, createResponse{Data: sc})
	}
}

// parsePayload is a simple parser for the studies configuration type
func parsePayload(b []byte) (sc types.StudyConf, err error) {
	if err := json.Unmarshal(b, &sc); err != nil {
		return sc, err
	}
	// runs validation against required fields
	//TODO: make error messages more readable
	validate = validator.New()
	if err = validate.Struct(sc); err != nil {
		return sc, err
	}

	return sc, nil
}
