import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import useStudy from '../../hooks/useStudy';
import StudyProgressStats from './StudyProgressStats';
import StudyProgressChart from './StudyProgressChart';
import ParticipantsAcquiredPerSegmentTable from './ParticipantsAcquiredPerSegmentTable';
import PageLayout from '../../components/PageLayout';
import ErrorPlaceholder from '../../components/ErrorPlaceholder';

/**
 * TODO: Implement proper scroll restoration behaviour
 *
 *  - When accessing a specific Study page through a link in the Studies page,
 *    the page should be scrolled to the top.
 *
 *  - When navigating from Study page to Studies page by clicking our custom back button,
 *    last scroll position of the Studies page should be restored.
 *
 *  - When navigating between Studies and Study page using browser back and forward button,
 *    last scroll position for the loaded page should be restored.
 */

const StudyPage = () => {
  const { studySlug } = useParams<{ studySlug: string }>();
  const study = useStudy(studySlug);
  const [selectedStat, setSelectedState] = useState('Current Participants');

  if (study.anyErrorDuringLoading) {
    return (
      <PageLayout title={''}>
        <ErrorPlaceholder
          message="Something went wrong while fetching the Study."
          onClickTryAgain={study.refetchData}
        />
      </PageLayout>
    );
  }

  return (
    <PageLayout
      showBackButton
      title={study.isLoading ? 'Loading...' : study.name}
    >
      <React.Fragment>
        <StudyProgressStats
          currentProgress={study.isLoading ? undefined : study.currentProgress}
          selectedStat={selectedStat}
          onSelectStat={newSelectedStat => {
            setSelectedState(newSelectedStat);
          }}
        />

        <StudyProgressChart
          label={selectedStat}
          data={study.isLoading ? undefined : study.progressOverTime}
        />

        <ParticipantsAcquiredPerSegmentTable />
      </React.Fragment>
    </PageLayout>
  );
};

export default StudyPage;
