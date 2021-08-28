package main

import (
	"encoding/json"
	"fmt"

	"github.com/tidwall/gjson"
)

type ExtractionFunctionParams interface {
	GetValue(json.RawMessage) ([]byte, error)
}

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
