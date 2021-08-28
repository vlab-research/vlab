package main

import (
	"github.com/stretchr/testify/assert"

	"testing"
)

func TestJsonSelectHappyPath(t *testing.T) {
	res, _ := JsonSelect([]byte(`{"foo": 2}`), "foo")
	assert.Equal(t, []byte(`2`), res)

	res, _ = JsonSelect([]byte(`{"foo": "2"}`), "foo")
	assert.Equal(t, []byte(`"2"`), res)

	res, _ = JsonSelect([]byte(`{"foo": "bar"}`), "foo")
	assert.Equal(t, []byte(`"bar"`), res)

	res, _ = JsonSelect([]byte(`{"foo": true}`), "foo")
	assert.Equal(t, []byte(`true`), res)

	res, _ = JsonSelect([]byte(`"foo"`), "")
	assert.Equal(t, []byte(`"foo"`), res)

	res, _ = JsonSelect([]byte(`2`), "")
	assert.Equal(t, []byte(`2`), res)
}

func TestJsonSelectMissingValueAtPath(t *testing.T) {
	_, err := JsonSelect([]byte(`{"foo": 2}`), "bar")
	assert.NotNil(t, err)

	_, err = JsonSelect([]byte(``), "")
	assert.NotNil(t, err)
}
