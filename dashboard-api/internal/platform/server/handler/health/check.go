package health

import (
	"database/sql"
	"net/http"

	"github.com/gin-gonic/gin"
)

type checkResponse struct {
	Healthy      bool                      `json:"healthy"`
	Dependencies checkResponseDependencies `json:"dependencies"`
}

type checkResponseDependencies []struct {
	Name    string `json:"name"`
	Healthy bool   `json:"healthy"`
}

func CheckHandler(db *sql.DB) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		isHealthy := true

		if err := db.PingContext(ctx); err != nil {
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
