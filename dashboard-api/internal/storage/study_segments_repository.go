package storage

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"math"
	"time"

	studiesmanager "github.com/vlab-research/vlab/dashboard-api/internal"
)

type StudySegmentsRepository struct {
	db *sql.DB
}

func NewStudySegmentsRepository(db *sql.DB) *StudySegmentsRepository {
	return &StudySegmentsRepository{
		db: db,
	}
}

type details map[string]struct {
	CurrentBudget              float64 `json:"current_budget"`
	DesiredPercentage          float64 `json:"desired_percentage"`
	CurrentPercentage          float64 `json:"current_percentage"`
	ExpectedPercentage         float64 `json:"expected_percentage"`
	DesiredParticipants        *int64  `json:"desired_participants"`
	CurrentParticipants        int64   `json:"current_participants"`
	ExpectedParticipants       float64 `json:"expected_participants"`
	CurrentPricePerParticipant float64 `json:"current_price_per_participant"`
}

func (r *StudySegmentsRepository) GetByStudySlug(
	ctx context.Context,
	slug, userID string,
) ([]studiesmanager.SegmentsProgress, error) {
	allTimeSegmentsProgress := []studiesmanager.SegmentsProgress{}
	errMsg := "error trying to get all time segments progress: %v"
	q := `
	SELECT a.created, a.details 
	FROM adopt_reports a
	JOIN studies s ON s.id = a.study_id 
	WHERE a.report_type = 'FACEBOOK_ADOPT' 
	AND s.slug = $1 
	AND s.user_id = $2
	ORDER BY created ASC
	`
	rows, err := r.db.Query(q, slug, userID)
	if err != nil {
		return nil, fmt.Errorf(errMsg, err)
	}

	defer rows.Close()

	for rows.Next() {
		var created time.Time
		var detailsInBytes []byte
		var details details

		if err := rows.Scan(&created, &detailsInBytes); err != nil {
			return nil, fmt.Errorf(errMsg, err)
		}

		err = json.Unmarshal(detailsInBytes, &details)
		if err != nil {
			return nil, fmt.Errorf(errMsg, err)
		}

		datetimeInMilliseconds := created.UnixMilli()
		segmentsProgress := studiesmanager.SegmentsProgress{
			Datetime: datetimeInMilliseconds,
			Segments: []studiesmanager.SegmentProgress{},
		}

		for segmentName, segmentProgress := range details {

			desiredPercentage := round(segmentProgress.DesiredPercentage)
			currentPercentage := round(segmentProgress.CurrentPercentage)

			segmentsProgress.Segments = append(segmentsProgress.Segments,
				studiesmanager.SegmentProgress{
					ID:                          segmentName,
					Name:                        segmentName,
					Datetime:                    datetimeInMilliseconds,
					CurrentBudget:               segmentProgress.CurrentBudget,
					DesiredPercentage:           desiredPercentage,
					CurrentPercentage:           currentPercentage,
					ExpectedPercentage:          round(segmentProgress.ExpectedPercentage),
					DesiredParticipants:         segmentProgress.DesiredParticipants,
					ExpectedParticipants:        int64(segmentProgress.ExpectedParticipants),
					CurrentParticipants:         segmentProgress.CurrentParticipants,
					CurrentPricePerParticipant:  segmentProgress.CurrentPricePerParticipant,
					PercentageDeviationFromGoal: round(math.Abs(desiredPercentage - currentPercentage)),
				})
		}

		allTimeSegmentsProgress = append(allTimeSegmentsProgress, segmentsProgress)

	}

	return allTimeSegmentsProgress, nil
}

func round(num float64) float64 {
	return math.Round(num*100) / 100
}
