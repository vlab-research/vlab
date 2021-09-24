package main

import (
	"encoding/json"
	"fmt"
	"strconv"

	"github.com/tidwall/gjson"
)

type ExtractionFunctionParams interface {
	GetValue(json.RawMessage) ([]byte, error)
}

// ---------------------------
// Select
// ---------------------------

type SelectFunctionParams struct {
	Path *string `json:"path" validate:"required"` // use pointer because "" is valid
}

func (p *SelectFunctionParams) GetValue(dat json.RawMessage) ([]byte, error) {
	return JsonSelect(dat, *p.Path)
}

func JsonSelect(dat json.RawMessage, path string) ([]byte, error) {
	if len(dat) == 0 {
		return nil, fmt.Errorf("Trying to extract value from empty json: %s", dat)
	}

	if path == "" {
		return dat, nil
	}

	val := gjson.GetBytes(dat, path).Raw

	if val == "" {
		return nil, fmt.Errorf("Trying to extract empty value via path %s in value json: %s", path, dat)
	}

	return []byte(val), nil

}

// ---------------------------
// Casting functions
// ---------------------------

func CastValue(b []byte) {

}
func CastContinuous(b []byte) (float64, error) {
	res := gjson.ParseBytes(b)
	switch res.Type {
	case gjson.Number:
		return res.Float(), nil
	case gjson.String:
		return strconv.ParseFloat(res.String(), 64)
	default:
		return 0, fmt.Errorf("Could not cast value as continuous: %s", string(b))
	}

}
