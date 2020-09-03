package main

import (
	"encoding/json"

	"github.com/confluentinc/confluent-kafka-go/kafka"
	"github.com/jackc/pgx/v4"
)



// TODO: 
// A) JSON Schema validation if you want validation... 
// OR
// B) Just validate the fields exist in the JSON (rawmessage, check all fields)
type Response struct {
	ParentSurveyid string `json:"parent_surveyid" validate:"required"`
	ParentShortcode *CastString `json:"parent_shortcode" validate:"required"`
	Surveyid string `json:"surveyid" validate:"required"`
	Shortcode *CastString `json:"shortcode" validate:"required"`
	Flowid int32 `json:"flowid" validate:"required"`
	Userid string `json:"userid" validate:"required"`
	QuestionRef string `json:"question_ref" validate:"required"`
	QuestionIdx int32 `json:"question_idx"` // no validate because 0 is valid...mierda
	QuestionText string `json:"question_text" validate:"required"`
	Response *CastString `json:"response" validate:"required"`
	Seed int64 `json:"seed" validate:"required"`
	Timestamp *JSTimestamp `json:"timestamp" validate:"required"`
	Metadata json.RawMessage `json:"metadata" validate:"required"`
}

func (r *Response) Queue(batch *pgx.Batch) {
	query := SertQuery("INSERT", "responses", []string{
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
	query += " ON CONFLICT(userid, timestamp, question_ref) DO NOTHING"

	batch.Queue(query,
		r.ParentSurveyid,
		r.ParentShortcode.String,
		r.Surveyid,
		r.Shortcode.String,
		r.Flowid,
		r.Userid,
		r.QuestionRef,
		r.QuestionIdx,
		r.QuestionText,
		r.Response.String,
		r.Seed,
		r.Timestamp.Time,
		r.Metadata)
}

func ResponseMarshaller(msg *kafka.Message) (Writeable, error) {
	m := new(Response)
	err := json.Unmarshal(msg.Value, m)
	if err != nil {
		return nil, err
	}

	return m, nil
}
