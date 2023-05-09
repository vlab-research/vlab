package main

import (
	"encoding/json"
	"fmt"
	"github.com/tidwall/gjson"
	"regexp"
	"strconv"
	"strings"
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
// vlab-kv-pair-select
// ---------------------------

type VlabKVPairSelectFunctionParams struct {
	Key string `json:"key" validate:"required"`
}

func (p *VlabKVPairSelectFunctionParams) GetValue(dat json.RawMessage) ([]byte, error) {
	var st string
	err := json.Unmarshal(dat, &st)
	if err != nil {
		return nil, fmt.Errorf("Bad KV Pair string: %s is not a string at all.", dat)
	}

	if st == "" {
		return nil, fmt.Errorf("Bad KV Pair string: %s was empty", st)
	}

	sli := strings.Split(st, ".")

	if len(sli)%2 != 0 {
		return nil, fmt.Errorf("Bad KV Pair string: %s has odd number of items", st)
	}

	pairs := map[string]string{}
	prev := ""

	for i, v := range sli {
		if i%2 == 0 {
			prev = v
		} else {
			pairs[prev] = v
		}
	}

	v, ok := pairs[p.Key]
	if !ok {
		return nil, fmt.Errorf("Could not extract KV Pair %s from string %s", p.Key, st)
	}

	// should not be possible for previous string to be unmarshallable
	b, _ := json.Marshal(v)

	return b, nil
}

// ---------------------------
// regexp-extract
// ---------------------------

type RegexpExtractParams struct {
	Regexp string `json:"regexp" validate:"required"`
}

func (p *RegexpExtractParams) GetValue(dat json.RawMessage) ([]byte, error) {
	m, err := regexp.Compile(p.Regexp)
	if err != nil {
		return nil, err
	}

	// This function only works if the value can be parsed as a json string
	var s string
	err = json.Unmarshal(dat, &s)
	if err != nil {
		return nil, fmt.Errorf("regexp-extract failed, the value could not be parsed as a string: %s. Original error: %s", dat, err)
	}

	res := m.FindString(s)

	if res == "" {
		return nil, fmt.Errorf("regexp-extract failed to find any value in the string: %s. For regular expression: %s", dat, p.Regexp)
	}

	// marshal back to JSON representation of a string
	ss, err := json.Marshal(res)
	if err != nil {
		return nil, err
	}
	return ss, nil
}

// ---------------------------
// Casting functions
// ---------------------------

func CastValue(conf *ExtractionConf, b []byte) ([]byte, error) {
	switch conf.ValueType {
	case "continuous":
		n, err := CastContinuous(b)
		if err != nil {
			return nil, err
		}
		return json.Marshal(n)

	default:
		return b, nil
	}

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
