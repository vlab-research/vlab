package types_test

import (
	"testing"

	"github.com/stretchr/testify/require"

	"github.com/vlab-research/vlab/dashboard-api/internal/testhelpers"

	"github.com/vlab-research/vlab/dashboard-api/internal/types"
)

func TestStudyConfType_TransformForDatabase(t *testing.T) {
	assert := require.New(t)
	t.Run("can transform an entire studyconf for database", func(t *testing.T) {
		input := testhelpers.NewStudyConf()
		expected := []types.DatabaseStudyConf{
			*testhelpers.NewDatabaseStudyConf(testhelpers.TypeGeneral()),
			*testhelpers.NewDatabaseStudyConf(testhelpers.TypeTargeting()),
			*testhelpers.NewDatabaseStudyConf(testhelpers.TypeTargetingDistribution()),
			*testhelpers.NewDatabaseStudyConf(testhelpers.TypeRecruitment()),
			*testhelpers.NewDatabaseStudyConf(testhelpers.TypeDestinations()),
			*testhelpers.NewDatabaseStudyConf(testhelpers.TypeCreatives()),
			*testhelpers.NewDatabaseStudyConf(testhelpers.TypeAudiences()),
		}
		s, err := input.TransformForDatabase()
		assert.NoError(err)
		assert.Equal(7, len(s))
		for i, _ := range s {
			assert.Equal(expected[i], s[i])
		}
	})
	t.Run("does not transform null confs", func(t *testing.T) {
		expected := []types.DatabaseStudyConf{
			*testhelpers.NewDatabaseStudyConf(testhelpers.TypeGeneral()),
			*testhelpers.NewDatabaseStudyConf(testhelpers.TypeTargeting()),
			*testhelpers.NewDatabaseStudyConf(testhelpers.TypeRecruitment()),
			*testhelpers.NewDatabaseStudyConf(testhelpers.TypeDestinations()),
			*testhelpers.NewDatabaseStudyConf(testhelpers.TypeCreatives()),
			*testhelpers.NewDatabaseStudyConf(testhelpers.TypeAudiences()),
		}
		input := testhelpers.NewStudyConf(testhelpers.WithTargetingDistributionConf(nil))
		s, err := input.TransformForDatabase()
		assert.NoError(err)
		assert.Equal(len(s), 6)
		for i, _ := range expected {
			assert.Equal(expected[i], s[i])
		}
	})
}

func TestStudyConfType_TransformFromDatabase(t *testing.T) {
	assert := require.New(t)
	t.Run("can transform an entire studyconf from databaseconfig", func(t *testing.T) {
		input := []*types.DatabaseStudyConf{
			testhelpers.NewDatabaseStudyConf(testhelpers.TypeGeneral()),
			testhelpers.NewDatabaseStudyConf(testhelpers.TypeTargeting()),
			testhelpers.NewDatabaseStudyConf(testhelpers.TypeTargetingDistribution()),
			testhelpers.NewDatabaseStudyConf(testhelpers.TypeDestinations()),
			testhelpers.NewDatabaseStudyConf(testhelpers.TypeRecruitment()),
			testhelpers.NewDatabaseStudyConf(testhelpers.TypeDestinations()),
			testhelpers.NewDatabaseStudyConf(testhelpers.TypeCreatives()),
			testhelpers.NewDatabaseStudyConf(testhelpers.TypeAudiences()),
		}
		expected := testhelpers.NewStudyConf()
		s := types.StudyConf{
			StudyID: testhelpers.StudyID,
			UserID:  testhelpers.CurrentUserId,
		}
		err := s.TransformFromDatabase(input)
		assert.NoError(err)
		assert.Equal(expected, s)
	})
}
