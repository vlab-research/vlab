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
	params := &VlabKVPairSelectFunctionParams{
		"bar",
	}

	v, e := params.GetValue([]byte(` "not.value.bar.baz"`))
	assert.Nil(t, e)
	assert.Equal(t, []byte(`"baz"`), v)
}

func TestVlabKVPairSelectParams_ErrorsIfNotExists(t *testing.T) {
	params := &VlabKVPairSelectFunctionParams{
		"bar",
	}

	_, e := params.GetValue([]byte(` "not.value"`))
	assert.NotNil(t, e)
	assert.Contains(t, e.Error(), "not.value")
	assert.Contains(t, e.Error(), "bar")
}

func TestVlabKVPairSelectParams_GetsNumbersAsStrings(t *testing.T) {
	params := &VlabKVPairSelectFunctionParams{
		"bar",
	}

	v, e := params.GetValue([]byte(` "bar.5"`))
	assert.Nil(t, e)
	assert.Equal(t, []byte(`"5"`), v)
}

func TestVlabKVPairSelectParams_ErrorsIfBadKVPairString(t *testing.T) {
	params := &VlabKVPairSelectFunctionParams{
		"bar",
	}

	_, e := params.GetValue([]byte(`"baz.bar.foo"`))
	assert.NotNil(t, e)
	assert.Contains(t, e.Error(), "baz.bar.foo")
}

func TestVlabKVPairSelectParams_ErrorsIfKVPairStringNotAString(t *testing.T) {
	params := &VlabKVPairSelectFunctionParams{
		"bar",
	}

	_, e := params.GetValue([]byte(`100`))
	assert.NotNil(t, e)
	assert.Contains(t, e.Error(), "100")
}

func TestVlabKVPairSelectParams_ErrorsIfKVPairStringEmpty(t *testing.T) {
	params := &VlabKVPairSelectFunctionParams{
		"bar",
	}

	_, e := params.GetValue([]byte(`""`))
	assert.NotNil(t, e)
	assert.Contains(t, e.Error(), "empty")
}

func TestRegexpExtractParams_ExtractsViaExpression(t *testing.T) {
	params := &RegexpExtractParams{Regexp: `\d+`}

	v, e := params.GetValue([]byte(`"123)"`))

	assert.Nil(t, e)
	assert.Equal(t, []byte(`"123"`), v)
}

func TestRegexpExtractParams_ErrorsIfNoValueExtracted(t *testing.T) {
	params := &RegexpExtractParams{Regexp: `\d+`}

	_, e := params.GetValue([]byte(`"abcd"`))

	assert.NotNil(t, e)
	assert.Contains(t, e.Error(), "failed to find")
}

func TestRegexpExtractParams_RaisesErrorIfValueNotAString(t *testing.T) {
	params := &RegexpExtractParams{Regexp: `\d+`}

	_, e := params.GetValue([]byte(`{"foo": "bar"}`))

	assert.NotNil(t, e)
	assert.Contains(t, e.Error(), "could not be parsed as a string")
}
