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
	CurrentBudget               int64   `json:"current_budget"`
	DesiredPercentage           float64 `json:"desired_percentage"`
	CurrentPercentage           float64 `json:"current_percentage"`
	ExpectedPercentage          float64 `json:"expected_percentage"`
	DesiredParticipants         *int64  `json:"desired_participants"`
	CurrentParticipants         int64   `json:"current_participants"`
	ExpectedParticipants        int64   `json:"expected_participants"`
	CurrentPricePerParticipants int64   `json:"current_price_per_participants"`
}

func (r *StudySegmentsRepository) GetAllTimeSegmentsProgress(ctx context.Context, studyId string) ([]studiesmanager.SegmentsProgress, error) {
	allTimeSegmentsProgress := []studiesmanager.SegmentsProgress{}

	rows, err := r.db.Query("SELECT created, details FROM adopt_reports WHERE report_type = 'FACEBOOK_ADOPT' and study_id = $1 ORDER BY created ASC", studyId)
	if err != nil {
		return nil, fmt.Errorf("(db.Query) error trying to get all time segments progress (studyId: %s): %v", studyId, err)
	}

	defer rows.Close()

	for rows.Next() {
		var created time.Time
		var detailsInBytes []byte
		var details details

		if err := rows.Scan(&created, &detailsInBytes); err != nil {
			return nil, fmt.Errorf("(rows.Scan) error trying to get all time segments progress (studyId: %s); %v", studyId, err)
		}

		err = json.Unmarshal(detailsInBytes, &details)
		if err != nil {
			return nil, fmt.Errorf("(json.Unmarshal) error trying to get all time segments progress (studyId: %s); %v", studyId, err)
		}

		datetimeInMilliseconds := created.UnixMilli()
		segmentsProgress := studiesmanager.SegmentsProgress{
			Datetime: datetimeInMilliseconds,
			Segments: []studiesmanager.SegmentProgress{},
		}

		for segmentName, segmentProgress := range details {
			desiredPercentage := round(segmentProgress.DesiredPercentage)
			currentPercentage := round(segmentProgress.CurrentPercentage)

			segmentsProgress.Segments = append(segmentsProgress.Segments, studiesmanager.SegmentProgress{
				Id:                          segmentName,
				Name:                        segmentName,
				Datetime:                    datetimeInMilliseconds,
				CurrentBudget:               segmentProgress.CurrentBudget,
				DesiredPercentage:           desiredPercentage,
				CurrentPercentage:           currentPercentage,
				ExpectedPercentage:          round(segmentProgress.ExpectedPercentage),
				DesiredParticipants:         segmentProgress.DesiredParticipants,
				ExpectedParticipants:        segmentProgress.ExpectedParticipants,
				CurrentParticipants:         segmentProgress.CurrentParticipants,
				CurrentPricePerParticipant:  segmentProgress.CurrentPricePerParticipants,
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
