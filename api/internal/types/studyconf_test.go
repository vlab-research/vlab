package types_test

import (
	"fmt"
	"testing"

	"github.com/stretchr/testify/require"

	"github.com/vlab-research/vlab/api/internal/testhelpers"

	"github.com/vlab-research/vlab/api/internal/types"
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
			*testhelpers.NewDatabaseStudyConf(testhelpers.TypeStrata()),
		}
		s, err := input.TransformForDatabase()
		assert.NoError(err)
		assert.Equal(8, len(s))
		for i, _ := range s {
			fmt.Printf("%s\n", s[i].Conf)
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
			*testhelpers.NewDatabaseStudyConf(testhelpers.TypeStrata()),
		}
		input := testhelpers.NewStudyConf(testhelpers.WithTargetingDistributionConf(nil))
		s, err := input.TransformForDatabase()
		assert.NoError(err)
		assert.Equal(len(s), 7)
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
			testhelpers.NewDatabaseStudyConf(testhelpers.TypeStrata()),
		}
		expected := testhelpers.NewStudyConf()
		s := types.StudyConf{
			StudyID: testhelpers.StudyID,
			UserID:  testhelpers.CurrentUserID,
		}
		err := s.TransformFromDatabase(input)
		assert.NoError(err)
		assert.Equal(expected, s)
	})
}
