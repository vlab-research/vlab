package main

import (
	"encoding/json"
	"github.com/jackc/pgx/v4"
)

type Response struct {
	ParentSurveyid string `json:"parent_surveyid" validate:"required"`
	ParentShortcode string `json:"parent_shortcode" validate:"required"`
	Surveyid string `json:"surveyid" validate:"required"`
	Shortcode string `json:"shortcode" validate:"required"`
	Flowid int32 `json:"flowid" validate:"required"`
	Userid string `json:"userid" validate:"required"`
	QuestionRef string `json:"question_ref" validate:"required"`
	QuestionIdx int32 `json:"question_idx" validate:"required"`
	QuestionText string `json:"question_text" validate:"required"`
	Response string `json:"response" validate:"required"`
	Seed int32 `json:"seed" validate:"required"`
	Timestamp int64 `json:"timestamp" validate:"required"`
	Metadata json.RawMessage `json:"metadata" validate:"required"`
}

func (r *Response) Queue(batch *pgx.Batch) {
	query := UpsertQuery("responses", []string{
		"parent_surveyid",
		"parent_shortcode",
		"surveyid",
		"shortcode",
		"flowid",
		"userid",
		"question_ref",
		"question_idx",
		"question_text",
		"response",
		"seed",
		"timestamp",
		"metadata",
	})

	batch.Queue(query,
		r.ParentSurveyid,
		r.ParentShortcode,
		r.Surveyid,
		r.Shortcode,
		r.Flowid,
		r.Userid,
		r.QuestionRef,
		r.QuestionIdx,
		r.QuestionText,
		r.Response,
		r.Seed,
		r.Timestamp,
		r.Metadata)
}


func ResponseMarshaller(b []byte) (Writeable, error) {
	state := new(Response)
	err := json.Unmarshal(b, state)
	if err != nil {
		return nil, err
	}

	return state, nil
}
