package users

import (
	"encoding/json"
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

type ExampleRequestBody struct {
	Clientid     string
	Clientsecret string
}

func SaveCredentials(repositories storage.Repositories) gin.HandlerFunc {
	return func(ctx *gin.Context) {

		var tuser ExampleRequestBody
		decoder := json.NewDecoder(ctx.Request.Body)
		err := decoder.Decode(&tuser)
		if err != nil {
			fmt.Printf("error %s", err)
			ctx.JSON(501, gin.H{"error": err})
		}

		fmt.Printf("Decoded Body Request Clientid : %v\n", tuser.Clientid)
		fmt.Printf("Decoded Body Request Clientsecret : %v\n", tuser.Clientsecret)

		_, err = repositories.Credentials.SaveCredentials(ctx, tuser.Clientid, tuser.Clientsecret)

		if err != nil {
			exa := err.Error()
			fmt.Println("exa: ", exa)
			fmt.Println("err ->", err)
		}

		ctx.JSON(http.StatusOK, createResponse{
			Data: "SaveCredentials...",
		})
	}
}
