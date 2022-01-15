package segmentsprogress_test

import (
	"errors"
	"net/http"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
	studiesmanager "github.com/vlab-research/vlab/dashboard-api/internal"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/storage"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/storage/storagemocks"
	"github.com/vlab-research/vlab/dashboard-api/internal/testhelpers"
)

func TestHandler_List(t *testing.T) {
	t.Run("should return a 404 when the study does not exist", func(t *testing.T) {
		studyRepository := new(storagemocks.StudyRepository)
		studySegmentsRepository := new(storagemocks.StudySegmentsRepository)
		studyRepository.On("GetStudyBySlug", mock.Anything, "inexistent-study", mock.Anything).Return(studiesmanager.Study{}, studiesmanager.ErrStudyNotFound)

		res := testhelpers.PerformGetRequest("/studies/inexistent-study/segments-progress", storage.Repositories{
			Study:         studyRepository,
			StudySegments: studySegmentsRepository,
		})

		assert.Equal(t, http.StatusNotFound, res.StatusCode)
	})

	t.Run("should return a 500 when the studyRepository returns an unexpected error", func(t *testing.T) {
		studyRepository := new(storagemocks.StudyRepository)
		studySegmentsRepository := new(storagemocks.StudySegmentsRepository)
		studyRepository.On("GetStudyBySlug", mock.Anything, "inexistent-study", mock.Anything).Return(studiesmanager.Study{}, errors.New("db timeout error"))

		res := testhelpers.PerformGetRequest("/studies/inexistent-study/segments-progress", storage.Repositories{
			Study:         studyRepository,
			StudySegments: studySegmentsRepository,
		})

		assert.Equal(t, http.StatusInternalServerError, res.StatusCode)
	})

	t.Run("should return a 500 when the studySegmentsRepository returns an unexpected error", func(t *testing.T) {
		studyRepository := new(storagemocks.StudyRepository)
		studySegmentsRepository := new(storagemocks.StudySegmentsRepository)
		study := studiesmanager.NewStudy("5372ca9c-9fcd-42d4-a596-d90792909917", "Example Study", "example-study", 1605049200000)
		studyRepository.On("GetStudyBySlug", mock.Anything, "example-study", mock.Anything).Return(study, nil)
		studySegmentsRepository.On("GetAllTimeSegmentsProgress", mock.Anything, study.Id).Return(nil, errors.New("db timeout error"))

		res := testhelpers.PerformGetRequest("/studies/example-study/segments-progress", storage.Repositories{
			Study:         studyRepository,
			StudySegments: studySegmentsRepository,
		})

		assert.Equal(t, http.StatusInternalServerError, res.StatusCode)
	})

	t.Run("should return a 200 with all-time segments progress for the specified study", func(t *testing.T) {
		studyRepository := new(storagemocks.StudyRepository)
		studySegmentsRepository := new(storagemocks.StudySegmentsRepository)
		study := studiesmanager.NewStudy("5372ca9c-9fcd-42d4-a596-d90792909917", "Example Study", "example-study", 1605049200000)
		studyRepository.On("GetStudyBySlug", mock.Anything, "example-study", mock.Anything).Return(study, nil)
		studySegmentsRepository.On("GetAllTimeSegmentsProgress", mock.Anything, study.Id).
			Return(
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
				nil,
			)

		res := testhelpers.PerformGetRequest("/studies/example-study/segments-progress", storage.Repositories{
			Study:         studyRepository,
			StudySegments: studySegmentsRepository,
		})

		assert.Equal(t, http.StatusOK, res.StatusCode)
		assert.Equal(t, "application/json; charset=utf-8", res.Header.Get("Content-Type"))
		assert.Equal(t, "{\"data\":[{\"segments\":[{\"id\":\"25-spain-male\",\"name\":\"25-spain-male\",\"datetime\":1605045600000,\"currentBudget\":72000,\"desiredPercentage\":5,\"currentPercentage\":0,\"expectedPercentage\":0,\"desiredParticipants\":null,\"expectedParticipants\":0,\"currentParticipants\":0,\"currentPricePerParticipant\":0,\"percentageDeviationFromGoal\":5}],\"datetime\":1605045600000},{\"segments\":[{\"id\":\"25-spain-male\",\"name\":\"25-spain-male\",\"datetime\":1605049200000,\"currentBudget\":72000,\"desiredPercentage\":5,\"currentPercentage\":8.25,\"expectedPercentage\":8.67,\"desiredParticipants\":null,\"expectedParticipants\":64,\"currentParticipants\":59,\"currentPricePerParticipant\":100,\"percentageDeviationFromGoal\":3.25}],\"datetime\":1605049200000}]}", res.Body)
	})

	t.Run("should return a 200 with an empty array when there are no segments-progress for the specified study", func(t *testing.T) {
		studyRepository := new(storagemocks.StudyRepository)
		studySegmentsRepository := new(storagemocks.StudySegmentsRepository)
		study := studiesmanager.NewStudy("5372ca9c-9fcd-42d4-a596-d90792909917", "Example Study", "example-study", 1605049200000)
		studyRepository.On("GetStudyBySlug", mock.Anything, "example-study", mock.Anything).Return(study, nil)
		studySegmentsRepository.On("GetAllTimeSegmentsProgress", mock.Anything, study.Id).
			Return(
				[]studiesmanager.SegmentsProgress{},
				nil,
			)

		res := testhelpers.PerformGetRequest("/studies/example-study/segments-progress", storage.Repositories{
			Study:         studyRepository,
			StudySegments: studySegmentsRepository,
		})

		assert.Equal(t, http.StatusOK, res.StatusCode)
		assert.Equal(t, "application/json; charset=utf-8", res.Header.Get("Content-Type"))
		assert.Equal(t, "{\"data\":[]}", res.Body)
	})
}
