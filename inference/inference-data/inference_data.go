package inference_data

import (
	"encoding/json"
	"time"
)

type User struct {
	ID       string                     `json:"id"`
	Metadata map[string]json.RawMessage `json:"metadata"`
}

type SourceConf struct {
	Name   string          `json:"name"`
	Source string          `json:"source"`
	Config json.RawMessage `json:"config"`
}

type Source struct {
	StudyID string
	Conf    *SourceConf
}

// DB reprsentation of configuration of data sources for a study
type DataSourceConf []*SourceConf

type InferenceDataEvent struct {
	User       User            `json:"user"`
	Study      string          `json:"study"`
	SourceConf *SourceConf     `json:"source_conf"`
	Timestamp  time.Time       `json:"timestamp"`
	Variable   string          `json:"variable"`
	Value      json.RawMessage `json:"value"`
	Idx        int             `json:"idx"`
	Pagination string          `json:"pagination"`
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
