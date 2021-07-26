package main

import (
	"encoding/json"
	"fmt"
	"github.com/stretchr/testify/assert"
	"io/ioutil"
	"testing"
	"time"
)

func testEvents(fi string) []*InferenceDataEvent {
	b, e := ioutil.ReadFile(fi)
	check(e)

	events := []InferenceDataEvent{}
	e = json.Unmarshal(b, &events)
	check(e)

	res := []*InferenceDataEvent{}

	for i, _ := range events {
		res = append(res, &events[i])
	}

	// return *events
	return res
}

func check(e error) {
	if e != nil {
		panic(e)
	}
}

func ti(day string) time.Time {
	t, e := time.Parse("2006-01-02", fmt.Sprintf("2021-07-%s", day))
	check(e)
	return t.UTC()
}

func TestReduceInferenceData(t *testing.T) {
	events := testEvents("events_a.json")

	expected := InferenceData{
		"foo": {"foo",
			map[string]*InferenceDataValue{
				"user_md": {ti("09"), "user_md", []byte(`"foo"`), "metadata"},
				"q1":      {ti("07"), "q1", []byte(`"A"`), "categorical"},
				"q2":      {ti("09"), "q2", []byte(`2`), "continuous"},
			}},
		"bar": {"bar",
			map[string]*InferenceDataValue{
				"user_md": {ti("10"), "user_md", []byte(`"bar"`), "metadata"},
				"q2":      {ti("10"), "q2", []byte(`2`), "continuous"},
			}},
	}

	actual := Reduce(events)

	assert.Equal(t, expected, actual)
}
