package main

import (
	"encoding/json"
	"github.com/stretchr/testify/assert"

	"strconv"
	"testing"
)

func check(e error) {
	if e != nil {
		panic(e)
	}
}

func TestLitDataTimestamp(t *testing.T) {
	b := []byte(strconv.Itoa(1668835896150040))

	v := new(LitDataTimestamp)
	json.Unmarshal(b, v)

	assert.Equal(t, 2022, v.Time.Year())
}
