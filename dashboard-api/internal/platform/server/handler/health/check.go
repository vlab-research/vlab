package health

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/storage"
)

type checkResponse struct {
	Healthy      bool                      `json:"healthy"`
	Dependencies checkResponseDependencies `json:"dependencies"`
}

type checkResponseDependencies []struct {
	Name    string `json:"name"`
	Healthy bool   `json:"healthy"`
}

func CheckHandler(repositories storage.Repositories) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		isHealthy := true

		if err := repositories.Db.PingContext(ctx); err != nil {
			isHealthy = false
		}

		ctx.JSON(http.StatusOK, checkResponse{
			Healthy: isHealthy,
			Dependencies: checkResponseDependencies{
				{
					Name:    "cockroachdb",
					Healthy: isHealthy,
				},
			},
		})
	}
}
