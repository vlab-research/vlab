package studies

import (
	"encoding/base64"
	"fmt"
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	studiesmanager "github.com/vlab-research/vlab/dashboard-api/internal"
)

type listResponse struct {
	Data       []studiesmanager.Study `json:"data"`
	Pagination listResponsePagination `json:"pagination"`
}

type listResponsePagination struct {
	NextCursor *string `json:"nextCursor"`
}

func ListHandler(studyRepository studiesmanager.StudyRepository) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		pagination, err := parsePaginationQueryParams(ctx)
		if err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		studies, err := studyRepository.GetStudies(ctx, pagination.Cursor, pagination.Number)
		if err != nil {
			ctx.Status(http.StatusInternalServerError)
			return
		}

		var nextCursor *string = nil
		if len(studies) >= pagination.Number {
			temp := createNextCursor(pagination)
			nextCursor = &temp
		}

		ctx.JSON(http.StatusOK, listResponse{
			Data: studies,
			Pagination: listResponsePagination{
				NextCursor: nextCursor,
			},
		})
	}
}

type paginationQueryParams struct {
	CursorInBase64url string `form:"cursor,default=MA==" binding:"base64url"`
	Number            int    `form:"number,default=20" binding:"gte=1,lte=100"`
}

type pagination struct {
	Cursor int
	Number int
}

func parsePaginationQueryParams(ctx *gin.Context) (pagination, error) {
	var params paginationQueryParams

	if err := ctx.ShouldBindQuery(&params); err != nil {
		return pagination{}, err
	}

	cursor, err := parseCursor(params.CursorInBase64url)
	if err != nil {
		return pagination{}, err
	}

	return pagination{
		Cursor: cursor,
		Number: params.Number,
	}, nil
}

func parseCursor(cursorInBase64url string) (int, error) {
	decodedCursorInBytes, err := base64.URLEncoding.DecodeString(cursorInBase64url)
	if err != nil {
		return 0, fmt.Errorf("invalid cursor: %s", cursorInBase64url)

	}

	cursor, err := strconv.Atoi(string(decodedCursorInBytes))
	if err != nil {
		return 0, fmt.Errorf("invalid cursor: %s", cursorInBase64url)
	}

	if cursor < 0 {
		return 0, fmt.Errorf("invalid cursor: %s", cursorInBase64url)
	}

	return cursor, nil
}

func createNextCursor(pagination pagination) string {
	nextCursorAsString := strconv.Itoa(pagination.Cursor + pagination.Number)

	return base64.URLEncoding.EncodeToString([]byte(nextCursorAsString))
}
