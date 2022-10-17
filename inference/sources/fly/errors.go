package main

import (
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"time"
)

type Timestamp time.Time

func (t *Timestamp) UnmarshalJSON(b []byte) error {
	format := "2006-01-02T15:04:05.000-0700"
	s := strings.Trim(string(b), "\"")
	parsed, err := time.Parse(format, s)
	if err != nil {
		return err
	}
	*t = Timestamp(parsed)
	return nil
}

type JSTimestamp time.Time

func (t *JSTimestamp) UnmarshalJSON(b []byte) error {
	var s string
	err := json.Unmarshal(b, &s)
	if err != nil {
		return err
	}

	i, err := strconv.ParseInt(s, 10, 64)
	if err != nil {
		return err
	}

	*t = JSTimestamp(time.Unix(0, i*1000000).UTC())
	return nil
}

// TODO: identityerrors return jstimestamp timestamp!!

type APIError struct {
	ErrorCode string `json:"errorCode,omitempty"`
	Message   string `json:"message,omitempty"`
	// TimeStamp *Timestamp `json:"timeStamp,omitempty"`
	InfoLink   string              `json:"infoLink,omitempty"`
	Path       string              `json:"path,omitempty"`
	StatusCode int                 `json:"statusCode,omitempty"`
	Details    []map[string]string `json:"details,omitempty"`
}

func (e APIError) Empty() bool {
	return e.ErrorCode == "" && e.Message == ""
}

func (e APIError) AddStatus(status int) APIError {
	e.StatusCode = status

	if e.ErrorCode == "" {
		e.ErrorCode = fmt.Sprint(status)
	}

	return e
}

func (e APIError) AsError() error {
	if e.Empty() {
		return nil
	}
	return e
}

func (e APIError) Error() string {
	return fmt.Sprintf("%v: %v", e.ErrorCode, e.Message)
}

type ReloadlyError struct {
	ErrorCode string
	Message   string
}

func (e ReloadlyError) Error() string {
	return fmt.Sprintf("%v: %v", e.ErrorCode, e.Message)
}
