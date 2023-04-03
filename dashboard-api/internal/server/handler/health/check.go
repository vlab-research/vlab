package health

import (
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/vlab-research/vlab/dashboard-api/internal/storage"
)

type checkResponse struct {
	Healthy      bool                      `json:"healthy"`
	Dependencies checkResponseDependencies `json:"dependencies"`
}

type checkResponseDependencies []struct {
	Name    string `json:"name"`
	Healthy bool   `json:"healthy"`
}

func CheckHandler(repositories storage.Repositories, auth0Domain string) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		cockroachdbHealthyStatus := isCockroachdbdbHealthy(ctx, repositories)
		auth0HealthyStatus := isAuth0Healthy(ctx, auth0Domain)

		healthyStatus := false
		if cockroachdbHealthyStatus && auth0HealthyStatus {
			healthyStatus = true
		}

		ctx.JSON(http.StatusOK, checkResponse{
			Healthy: healthyStatus,
			Dependencies: checkResponseDependencies{
				{
					Name:    "cockroachdb",
					Healthy: cockroachdbHealthyStatus,
				},
				{
					Name:    "auth0",
					Healthy: auth0HealthyStatus,
				},
			},
		})
	}
}

func isCockroachdbdbHealthy(ctx *gin.Context, repositories storage.Repositories) bool {
	if err := repositories.Db.PingContext(ctx); err != nil {
		return false
	}

	return true
}

func isAuth0Healthy(ctx *gin.Context, auth0Domain string) bool {
	request, err := http.NewRequest(http.MethodGet, fmt.Sprintf("%s.well-known/jwks.json", auth0Domain), nil)
	if err != nil {
		return false
	}

	request = request.WithContext(ctx)

	response, err := http.DefaultClient.Do(request)
	if err != nil {
		return false
	}

	if response.StatusCode != http.StatusOK {
		return false
	}

	return true
}
