package users

import (
	"errors"
	"fmt"
	"log"
	"net/http"

	"github.com/gin-gonic/gin"
	studiesmanager "github.com/vlab-research/vlab/dashboard-api/internal"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/server/middleware/auth"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/storage"
)

type createResponse struct {
	Data interface{} `json:"data"`
}

func CreateHandler(repositories storage.Repositories) gin.HandlerFunc {

	return func(ctx *gin.Context) {
		user, err := repositories.User.CreateUser(ctx, auth.GetUserIdFrom(ctx))

		if err != nil {
			switch {
			case errors.Is(err, studiesmanager.ErrUserAlreadyExists):
				ctx.JSON(http.StatusUnprocessableEntity, gin.H{"error": "User already exists"})
				return
			default:
				log.Printf(err.Error())
				ctx.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
		}

		ctx.JSON(http.StatusCreated, createResponse{
			Data: user,
		})
	}
}

func SaveCredentials(repositories storage.Repositories) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		user, err := repositories.Credentials.SaveCredentials(ctx, "123", "clientSecret")

		if err != nil {
			exa := err.Error()
			fmt.Println("exa: ", exa)
			fmt.Println("err ->", err)
		}

		fmt.Println("user ->", user)

		ctx.JSON(http.StatusOK, createResponse{
			Data: "SaveCredentials...",
		})
	}
}
