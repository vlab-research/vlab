package main

import (
	"github.com/stretchr/testify/assert"

	"testing"
)

func TestJsonSelect_HappyPath(t *testing.T) {
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

func TestJsonSelect_MissingValueAtPath(t *testing.T) {
	_, err := JsonSelect([]byte(`{"foo": 2}`), "bar")
	assert.NotNil(t, err)

	_, err = JsonSelect([]byte(``), "")
	assert.NotNil(t, err)
}

func TestCastContinuous_CastsAllValues(t *testing.T) {
	f, err := CastContinuous([]byte(`2`))
	assert.Nil(t, err)
	assert.Equal(t, 2.0, f)

	f, err = CastContinuous([]byte(`"2"`))
	assert.Nil(t, err)
	assert.Equal(t, 2.0, f)
}

func TestCastContinuous_ErrorsWhenNotPossible(t *testing.T) {
	_, err := CastContinuous([]byte(`{"foo": "bar"}`))
	assert.NotNil(t, err)

	_, err = CastContinuous([]byte(`"foo"`))
	assert.NotNil(t, err)
}

func TestVlabKVPairSelectParams_SplitAndGetIfExists(t *testing.T) {
	s := "foo"
	params := &VlabKVPairSelectFunctionParams{
		&s,
		"bar",
	}

	v, e := params.GetValue([]byte(`{"foo": "not.value.bar.baz"}`))
	assert.Nil(t, e)
	assert.Equal(t, []byte(`"baz"`), v)
}

func TestVlabKVPairSelectParams_ErrorsIfNotExists(t *testing.T) {
	s := "foo"
	params := &VlabKVPairSelectFunctionParams{
		&s,
		"bar",
	}

	_, e := params.GetValue([]byte(`{"foo": "not.value"}`))
	assert.NotNil(t, e)
	assert.Contains(t, e.Error(), "not.value")
	assert.Contains(t, e.Error(), "bar")
}

func TestVlabKVPairSelectParams_GetsNumbersAsStrings(t *testing.T) {
	s := "foo"
	params := &VlabKVPairSelectFunctionParams{
		&s,
		"bar",
	}

	v, e := params.GetValue([]byte(`{"foo": "bar.5"}`))
	assert.Nil(t, e)
	assert.Equal(t, []byte(`"5"`), v)
}

func TestVlabKVPairSelectParams_ErrorsIfBadKVPairString(t *testing.T) {
	s := "foo"
	params := &VlabKVPairSelectFunctionParams{
		&s,
		"bar",
	}

	_, e := params.GetValue([]byte(`{"foo": "baz.bar.foo"}`))
	assert.NotNil(t, e)
	assert.Contains(t, e.Error(), "baz.bar.foo")
}

func TestVlabKVPairSelectParams_ErrorsIfKVPairStringNotAString(t *testing.T) {
	s := "foo"
	params := &VlabKVPairSelectFunctionParams{
		&s,
		"bar",
	}

	_, e := params.GetValue([]byte(`{"foo": 100}`))
	assert.NotNil(t, e)
	assert.Contains(t, e.Error(), "100")
}
