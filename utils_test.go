package main

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestPlaceholders(t *testing.T) {

	p := Placeholders(1, 1)
	assert.Equal(t, "($1)", p)

	p = Placeholders(2, 1)
	assert.Equal(t, "($1,$2)", p)

	p = Placeholders(1, 2)
	assert.Equal(t, "($1),($2)", p)

	p = Placeholders(2, 2)
	assert.Equal(t, "($1,$2),($3,$4)", p)

}
