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
		}
		s, err := input.TransformForDatabase()
		assert.NoError(err)
		for i, _ := range expected {
			assert.Equal(expected[i], s[i])
		}
	})
	t.Run("does not transform null confs", func(t *testing.T) {
		expected := []types.DatabaseStudyConf{
			*testhelpers.NewDatabaseStudyConf(testhelpers.TypeGeneral()),
			*testhelpers.NewDatabaseStudyConf(testhelpers.TypeTargeting()),
		}
		input := testhelpers.NewStudyConf(testhelpers.WithTargetingDistributionConf(nil))
		s, err := input.TransformForDatabase()
		assert.NoError(err)
		assert.Equal(len(s), 2)
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
