package users

import (
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	studiesmanager "github.com/vlab-research/vlab/dashboard-api/internal"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/server/middleware/auth"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/storage"
)

type createResponse struct {
	Data interface{} `json:"data"`
}

type RequestBody struct {
	Clientid     string
	Clientsecret string
	NickName     string
	Accesstoken  string
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
		var tuser RequestBody
		tconnector := ctx.Query("type")

		decoder := json.NewDecoder(ctx.Request.Body)
		err := decoder.Decode(&tuser)
		if err != nil {
			fmt.Printf("error %s", err)
			ctx.JSON(501, gin.H{"error": err})
		}

		switch strings.ToLower(tconnector) {
		case "fly":
			_, err = repositories.UserSaveCredentials.SaveCredentialsFly(ctx, tuser.Clientid, tuser.NickName)
		case "typeform":
			_, err = repositories.UserSaveCredentials.SaveCredentialsFly(ctx, tuser.Accesstoken, tuser.NickName)
		}

		fmt.Printf("Decoded Body Request Clientid: %v\n", tuser.Clientid)
		fmt.Printf("Decoded Body Request NickName: %v\n", tuser.NickName)
		fmt.Printf("Decoded Body Request Accesstoken : %v\n", tuser.Accesstoken)

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

func GetCredentials(repositories storage.Repositories) gin.HandlerFunc {
	return func(ctx *gin.Context) {

		clientId := "auth0|47016c1dab79c900713937fa"

		credentials, err := repositories.GetCredentials.GetCredentials(ctx, clientId)

		if err != nil {
			ctx.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		ctx.JSON(http.StatusOK, createResponse{
			Data: credentials,
		})
	}
}
