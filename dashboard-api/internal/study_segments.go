package studiesmanager

import "context"

type StudySegmentsRepository interface {
	GetAllTimeSegmentsProgress(ctx context.Context, studyId string) ([]SegmentsProgress, error)
}

//go:generate mockery --case=snake --outpkg=storagemocks --output=platform/storage/storagemocks --name=StudySegmentsRepository

type SegmentsProgress struct {
	Segments []SegmentProgress `json:"segments"`
	Datetime int64             `json:"datetime"`
}

type SegmentProgress struct {
	Id                          string  `json:"id"`
	Name                        string  `json:"name"`
	Datetime                    int64   `json:"datetime"`
	CurrentBudget               int64   `json:"currentBudget"`
	DesiredPercentage           float64 `json:"desiredPercentage"`
	CurrentPercentage           float64 `json:"currentPercentage"`
	ExpectedPercentage          float64 `json:"expectedPercentage"`
	DesiredParticipants         *int64  `json:"desiredParticipants"`
	ExpectedParticipants        int64   `json:"expectedParticipants"`
	CurrentParticipants         int64   `json:"currentParticipants"`
	CurrentPricePerParticipant  int64   `json:"currentPricePerParticipant"`
	PercentageDeviationFromGoal float64 `json:"percentageDeviationFromGoal"`
}
