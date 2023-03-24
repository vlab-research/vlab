package helpers

import (
	"encoding/base64"
	"fmt"
	"strconv"

	"github.com/gin-gonic/gin"
)

type paginationQueryParams struct {
	CursorInBase64url string `form:"cursor,default=MA==" binding:"base64url"`
	Number            int    `form:"number,default=20" binding:"gte=1,lte=100"`
}

func NewPagination() *Pagination {
	return &Pagination{}
}

type ListResponsePagination struct {
	NextCursor *string `json:"nextCursor"`
}

type Pagination struct {
	Cursor int
	Number int
}

func (p *Pagination) ParseQueryParams(ctx *gin.Context) error {
	var params paginationQueryParams
	if err := ctx.ShouldBindQuery(&params); err != nil {
		return err
	}

	cursor, err := parseCursor(params.CursorInBase64url)
	if err != nil {
		return err
	}

	p.Cursor = cursor
	p.Number = params.Number
	return nil
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

func (p *Pagination) CreateNextCursor() *string {
	nextCursorAsString := strconv.Itoa(p.Cursor + p.Number)
	c := base64.URLEncoding.EncodeToString([]byte(nextCursorAsString))
	return &c
}
