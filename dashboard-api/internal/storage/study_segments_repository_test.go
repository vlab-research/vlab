package storage

import (
	"context"
	"encoding/json"
	"errors"
	"testing"
	"time"

	"github.com/DATA-DOG/go-sqlmock"
	"github.com/stretchr/testify/require"
	"github.com/vlab-research/vlab/dashboard-api/internal/types"
)

const (
	studyslug = "example-study"
	userID    = "1234"
	q         = `
	SELECT a.created, a.details 
	FROM adopt_reports a
	JOIN studies s ON s.id = a.study_id 
	WHERE a.report_type = 'FACEBOOK_ADOPT' 
	AND s.slug = $1 
	AND s.user_id = $2
	ORDER BY created ASC
	`
)

func Test_StudySegmentsRepository_GetAllTimeSegmentsProgress_UnexpectedError_during_Query(t *testing.T) {
	assert := require.New(t)
	db, sqlMock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherEqual))
	assert.NoError(err)

	sqlMock.ExpectQuery(q).
		WithArgs(studyslug, userID).
		WillReturnError(errors.New("unexpected-error"))

	r := NewStudySegmentsRepository(db)

	_, err = r.GetByStudySlug(context.TODO(), studyslug, userID)

	assert.NoError(sqlMock.ExpectationsWereMet())
	expected := errors.New("error trying to get all time segments progress: unexpected-error")
	assert.Equal(expected, err)
}

func Test_StudySegmentsRepository_GetAllTimeSegmentsProgress_UnexpectedError_during_Scan(t *testing.T) {
	assert := require.New(t)
	db, sqlMock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherEqual))
	assert.NoError(err)

	rows := sqlMock.NewRows([]string{"created"}).
		AddRow(time.Now())

	sqlMock.ExpectQuery(q).
		WithArgs(studyslug, userID).
		WillReturnRows(rows)

	r := NewStudySegmentsRepository(db)

	_, err = r.GetByStudySlug(context.TODO(), studyslug, userID)

	assert.NoError(sqlMock.ExpectationsWereMet())
	assert.Equal(errors.New("error trying to get all time segments progress: sql: expected 1 destination arguments in Scan, not 2"), err)
}

func Test_StudySegmentsRepository_GetAllTimeSegmentsProgress_Succeed(t *testing.T) {
	assert := require.New(t)
	db, sqlMock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherEqual))
	assert.NoError(err)

	oldestDetails := details{"25-spain-male": {
		CurrentBudget:              72000,
		DesiredPercentage:          5,
		CurrentPercentage:          0,
		ExpectedPercentage:         0,
		DesiredParticipants:        nil,
		CurrentParticipants:        0,
		ExpectedParticipants:       0,
		CurrentPricePerParticipant: 0,
	}}
	oldestDetailsInBytes, err := json.Marshal(oldestDetails)
	require.NoError(t, err)
	mostRecentDetails := details{"25-spain-male": {
		CurrentBudget:              72000,
		DesiredPercentage:          5,
		CurrentPercentage:          8.25,
		ExpectedPercentage:         8.67,
		DesiredParticipants:        nil,
		CurrentParticipants:        59,
		ExpectedParticipants:       64,
		CurrentPricePerParticipant: 100,
	}}
	mostRecentDetailsInBytes, err := json.Marshal(mostRecentDetails)
	require.NoError(t, err)

	rows := sqlMock.NewRows([]string{"created", "details"}).
		AddRow(time.Date(2020, time.November, 10, 22, 0, 0, 0, time.UTC), oldestDetailsInBytes).
		AddRow(time.Date(2020, time.November, 10, 23, 0, 0, 0, time.UTC), mostRecentDetailsInBytes)

	sqlMock.ExpectQuery(q).
		WithArgs(studyslug, userID).
		WillReturnRows(rows)

	r := NewStudySegmentsRepository(db)

	spList, err := r.GetByStudySlug(context.TODO(), studyslug, userID)

	assert.NoError(sqlMock.ExpectationsWereMet())
	assert.NoError(err)
	assert.Equal(
		[]types.SegmentsProgress(
			[]types.SegmentsProgress{
				{
					Segments: []types.SegmentProgress{
						{
							ID:                          "25-spain-male",
							Name:                        "25-spain-male",
							Datetime:                    1605045600000,
							CurrentBudget:               72000,
							DesiredPercentage:           5,
							CurrentPercentage:           0,
							ExpectedPercentage:          0,
							DesiredParticipants:         (*int64)(nil),
							ExpectedParticipants:        0,
							CurrentParticipants:         0,
							CurrentPricePerParticipant:  0,
							PercentageDeviationFromGoal: 5,
						},
					},
					Datetime: 1605045600000,
				},
				{
					Segments: []types.SegmentProgress{
						{
							ID:                          "25-spain-male",
							Name:                        "25-spain-male",
							Datetime:                    1605049200000,
							CurrentBudget:               72000,
							DesiredPercentage:           5,
							CurrentPercentage:           8.25,
							ExpectedPercentage:          8.67,
							DesiredParticipants:         (*int64)(nil),
							ExpectedParticipants:        64,
							CurrentParticipants:         59,
							CurrentPricePerParticipant:  100,
							PercentageDeviationFromGoal: 3.25,
						},
					},
					Datetime: 1605049200000,
				},
			},
		),
		spList,
	)
}
