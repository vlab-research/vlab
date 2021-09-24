package main

import (
	"encoding/json"
	"time"
)

// Connectors for individual recruitment platforms (i.e. Facebook)
// (this should be in Python using facebook python sdk)

// Individual event about recruitment process
// RecruitmentDataEvent
type TimePeriod struct {
	Start time.Time `json:"start"`
	End   time.Time `json:"end"`
}

type RecruitmentDataEvent struct {
	StudyID    string          `json:"study_id"`
	Source     string          `json:"source"`
	Integrity  int64           `json:"integrity"` // 0,1,2,3,4...
	TimePeriod TimePeriod      `json:"time_period"`
	Data       json.RawMessage `json:"data"`
}

// integrity acts like "priority", such that higher integrity data for the
// same time period replaces lower integrity data.

// this is meant to handle "temp" data (intra-day) and replace it later
// with "historical" data (after the day is over).

// Reduce is primarily in charge of managing the integrity problem
// to ensure that the current data is exactly the version we care about.

// Reduce input: []RecruitmentDataEvent
// Reduce ouputs:
// RecruitmentData
