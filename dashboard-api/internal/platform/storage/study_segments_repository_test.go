package storage

import (
	"context"
	"encoding/json"
	"errors"
	"testing"
	"time"

	"github.com/DATA-DOG/go-sqlmock"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	studiesmanager "github.com/vlab-research/vlab/dashboard-api/internal"
)

func Test_StudySegmentsRepository_GetAllTimeSegmentsProgress_UnexpectedError_during_Query(t *testing.T) {
	studyId := "c463c577-a3d1-482e-b638-10e6733e2325"
	db, sqlMock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherEqual))
	require.NoError(t, err)

	sqlMock.ExpectQuery(
		"SELECT created, details FROM adopt_reports WHERE report_type = 'FACEBOOK_OPTIMIZATION' and study_id = $1 ORDER BY created ASC").
		WithArgs(studyId).
		WillReturnError(errors.New("unexpected-error"))

	repo := NewStudySegmentsRepository(db)

	_, err = repo.GetAllTimeSegmentsProgress(context.Background(), studyId)

	assert.NoError(t, sqlMock.ExpectationsWereMet())
	assert.Equal(t, errors.New("(db.Query) error trying to get all time segments progress (studyId: c463c577-a3d1-482e-b638-10e6733e2325): unexpected-error"), err)
}

func Test_StudySegmentsRepository_GetAllTimeSegmentsProgress_UnexpectedError_during_Scan(t *testing.T) {
	studyId := "c463c577-a3d1-482e-b638-10e6733e2325"
	db, sqlMock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherEqual))
	require.NoError(t, err)

	rows := sqlMock.NewRows([]string{"created"}).
		AddRow(time.Now())

	sqlMock.ExpectQuery(
		"SELECT created, details FROM adopt_reports WHERE report_type = 'FACEBOOK_OPTIMIZATION' and study_id = $1 ORDER BY created ASC").
		WithArgs(studyId).
		WillReturnRows(rows)

	repo := NewStudySegmentsRepository(db)

	_, err = repo.GetAllTimeSegmentsProgress(context.Background(), studyId)

	assert.NoError(t, sqlMock.ExpectationsWereMet())
	assert.Equal(t, errors.New("(rows.Scan) error trying to get all time segments progress (studyId: c463c577-a3d1-482e-b638-10e6733e2325); sql: expected 1 destination arguments in Scan, not 2"), err)
}

func Test_StudySegmentsRepository_GetAllTimeSegmentsProgress_Succeed(t *testing.T) {
	studyId := "c463c577-a3d1-482e-b638-10e6733e2325"
	db, sqlMock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherEqual))
	require.NoError(t, err)

	oldestDetails := details{"25-spain-male": {
		CurrentBudget:               72000,
		DesiredPercentage:           5,
		CurrentPercentage:           0,
		ExpectedPercentage:          0,
		DesiredParticipants:         nil,
		CurrentParticipants:         0,
		ExpectedParticipants:        0,
		CurrentPricePerParticipants: 0,
	}}
	oldestDetailsInBytes, err := json.Marshal(oldestDetails)
	require.NoError(t, err)
	mostRecentDetails := details{"25-spain-male": {
		CurrentBudget:               72000,
		DesiredPercentage:           5,
		CurrentPercentage:           8.25,
		ExpectedPercentage:          8.67,
		DesiredParticipants:         nil,
		CurrentParticipants:         59,
		ExpectedParticipants:        64,
		CurrentPricePerParticipants: 100,
	}}
	mostRecentDetailsInBytes, err := json.Marshal(mostRecentDetails)
	require.NoError(t, err)

	rows := sqlMock.NewRows([]string{"created", "details"}).
		AddRow(time.Date(2020, time.November, 10, 22, 0, 0, 0, time.UTC), oldestDetailsInBytes).
		AddRow(time.Date(2020, time.November, 10, 23, 0, 0, 0, time.UTC), mostRecentDetailsInBytes)

	sqlMock.ExpectQuery(
		"SELECT created, details FROM adopt_reports WHERE report_type = 'FACEBOOK_OPTIMIZATION' and study_id = $1 ORDER BY created ASC").
		WithArgs(studyId).
		WillReturnRows(rows)

	repo := NewStudySegmentsRepository(db)

	allTimeSegmentsProgress, err := repo.GetAllTimeSegmentsProgress(context.Background(), studyId)

	assert.NoError(t, sqlMock.ExpectationsWereMet())
	assert.NoError(t, err)
	assert.Equal(
		t,
		[]studiesmanager.SegmentsProgress(
			[]studiesmanager.SegmentsProgress{
				{
					Segments: []studiesmanager.SegmentProgress{
						{
							Id:                          "25-spain-male",
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
					Segments: []studiesmanager.SegmentProgress{
						{
							Id:                          "25-spain-male",
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
		allTimeSegmentsProgress,
	)
}
