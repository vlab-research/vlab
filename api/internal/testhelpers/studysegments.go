package testhelpers

import (
	"encoding/json"
	"testing"
	"time"

	"github.com/vlab-research/vlab/api/internal/types"
)

type details map[string]segment

type segment struct {
	CurrentBudget              float64 `json:"current_budget"`
	DesiredPercentage          float64 `json:"desired_percentage"`
	CurrentPercentage          float64 `json:"current_percentage"`
	ExpectedPercentage         float64 `json:"expected_percentage"`
	DesiredParticipants        *int64  `json:"desired_participants"`
	CurrentParticipants        int64   `json:"current_participants"`
	ExpectedParticipants       float64 `json:"expected_participants"`
	CurrentPricePerParticipant float64 `json:"current_price_per_participant"`
}

func DeleteAllStudySegments(t *testing.T) {
	t.Helper()
	r := GetRepositories()
	r.Db.Exec("DELETE FROM adopt_reports")
}

func CreateSegment(t *testing.T, sp []types.SegmentsProgress) error {
	t.Helper()
	r := GetRepositories()
	q := `
  INSERT INTO adopt_reports (study_id, created, details, report_type) 
	VALUES ($1, $2, $3, 'FACEBOOK_ADOPT')
	`
	for _, p := range sp {
		d := make(details)
		for _, s := range p.Segments {
			d[s.Name] = segment{
				CurrentBudget:              s.CurrentBudget,
				DesiredPercentage:          s.DesiredPercentage,
				CurrentPercentage:          s.CurrentPercentage,
				ExpectedPercentage:         s.ExpectedPercentage,
				DesiredParticipants:        s.DesiredParticipants,
				CurrentParticipants:        s.CurrentParticipants,
				ExpectedParticipants:       float64(s.ExpectedParticipants),
				CurrentPricePerParticipant: s.CurrentPricePerParticipant,
			}
		}
		b, err := json.Marshal(d)
		if err != nil {
			return err
		}
		_, err = r.Db.Exec(q, StudyID, time.Unix(p.Datetime, 0), string(b))
		if err != nil {
			return err
		}
	}
	return nil
}
