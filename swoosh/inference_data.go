package main

import (
	"encoding/json"
	"time"
)

type User struct {
	ID       string                     `json:"id"`
	Metadata map[string]json.RawMessage `json:"metadata"`
}

type InferenceDataEvent struct {
	User      User            `json:"user"`
	Study     string          `json:"study"`
	Timestamp time.Time       `json:"timestamp"`
	Variable  string          `json:"variable"`
	ValueType string          `json:"value_type"`
	Value     json.RawMessage `json:"value"`
	Metadata  json.RawMessage `json:"metadata"`
}

type StudyDataSource struct {
	Name   string
	Params json.RawMessage
}

type StudyConf struct {
	Sources   []StudyDataSource
	Variables []string // must have variables, to be included in study
}

type InferenceDataValue struct {
	Timestamp time.Time       `json:"timestamp"`
	Variable  string          `json:"variable"`
	Value     json.RawMessage `json:"value"`
	ValueType string          `json:"value_type"`
}

type InferenceDataRow struct {
	User string                         `json:"user"`
	Data map[string]*InferenceDataValue `json:"data"`
}

type InferenceData map[string]*InferenceDataRow

func addValue(id InferenceData, user string, val *InferenceDataValue) InferenceData {
	_, ok := id[user]

	if !ok {
		id[user] = &InferenceDataRow{user, make(map[string]*InferenceDataValue)}
	}

	id[user].Data[val.Variable] = val
	return id
}

func extractValues(e *InferenceDataEvent) []*InferenceDataValue {
	vals := []*InferenceDataValue{}

	for k, v := range e.User.Metadata {
		vals = append(vals, &InferenceDataValue{e.Timestamp, k, v, "metadata"})
	}

	vals = append(vals, &InferenceDataValue{e.Timestamp, e.Variable, e.Value, e.ValueType})

	return vals
}

// TODO: filter based on config (adattribution data, has variable x, etc.)
func Reduce(events []*InferenceDataEvent) InferenceData {
	id := make(InferenceData)

	for _, e := range events {
		vals := extractValues(e)
		for _, v := range vals {
			addValue(id, e.User.ID, v)
		}
	}

	return id
}
