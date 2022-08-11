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
	Clientid     string `json:"clientId" validate:"required"`
	Clientsecret string `json:"clientSecret" validate:"required"`
	NickName     string `json:"nickName" validate:"required"`
	Accesstoken  string `json:"accesstoken"`
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

		if tconnector == "" {
			tconnector = "fly"
		}

		decoder := json.NewDecoder(ctx.Request.Body)
		err := decoder.Decode(&tuser)
		if err != nil {
			fmt.Printf("error %s", err)
			ctx.JSON(400, gin.H{"error": "You have not satisfied the structure"})
			return
		}

		switch strings.ToLower(tconnector) {
		case "fly":
			_, err = repositories.SaveCredentialsFly.SaveCredentialsFly(ctx, tuser.Clientid, tuser.NickName)
			if err != nil {
				fmt.Println("fly err ->", err)
				ctx.JSON(401, gin.H{"error": err.Error()})
				return
			}
		case "typeform":
			_, err = repositories.SaveCredentialsTypeform.SaveCredentialsTypeform(ctx, tuser.Accesstoken, tuser.NickName)
			if err != nil {
				fmt.Println("typeform err ->", err)
				ctx.JSON(401, gin.H{"error": err})
				return
			}

		}

		ctx.JSON(http.StatusOK, createResponse{
			Data: "Credentials successfully saved!",
		})
	}
}

func GetCredentials(repositories storage.Repositories) gin.HandlerFunc {
	return func(ctx *gin.Context) {

		var tuser RequestBody

		err := json.NewDecoder(ctx.Request.Body).Decode(&tuser)
		if err != nil {
			println(err)
		}

		credentials, err := repositories.GetCredentials.GetCredentials(ctx, tuser.Clientid)

		if err != nil {
			ctx.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		ctx.JSON(http.StatusOK, createResponse{
			Data: credentials,
		})
	}
}
