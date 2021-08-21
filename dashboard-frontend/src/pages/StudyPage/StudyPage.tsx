import React, { useState } from 'react';
import { queryCache } from 'react-query';
import { useParams } from 'react-router-dom';
import useStudyQuery from './useStudyQuery';
import useStudyProgressQuery from './useStudyProgressQuery';
import useStudySegmentsProgressQuery from './useStudySegmentsProgressQuery';
import StudyProgressStats from './StudyProgressStats';
import StudyProgressChart from './StudyProgressChart';
import StudySegmentsTables from './StudySegmentsTables';
import PageLayout from '../../components/PageLayout';
import ErrorPlaceholder from '../../components/ErrorPlaceholder';
import { lastValue } from '../../helpers/arrays';

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
  const studyQuery = useStudyQuery(studySlug);
  const studyProgressQuery = useStudyProgressQuery(studySlug);
  const studySegmentsProgressQuery = useStudySegmentsProgressQuery(studySlug);
  const [selectedStat, setSelectedState] = useState('Current Participants');

  const isFirstTimeLoad =
    !studyQuery.data ||
    !studyProgressQuery.data?.length ||
    !studySegmentsProgressQuery.resolvedData;

  const anyErrorDuringFirstTimeLoad =
    isFirstTimeLoad &&
    (studyQuery.isError ||
      studyProgressQuery.isError ||
      studySegmentsProgressQuery.isError);

  if (anyErrorDuringFirstTimeLoad) {
    return (
      <PageLayout title={''}>
        <ErrorPlaceholder
          message="Something went wrong while fetching the Study."
          onClickTryAgain={() => {
            queryCache.invalidateQueries(['study', studySlug]);
          }}
        />
      </PageLayout>
    );
  }

  return (
    <PageLayout
      showBackButton
      title={isFirstTimeLoad ? 'Loading...' : studyQuery.data!.name}
    >
      <React.Fragment>
        <StudyProgressStats
          currentProgress={
            isFirstTimeLoad ? undefined : lastValue(studyProgressQuery.data!)
          }
          selectedStat={selectedStat}
          onSelectStat={newSelectedStat => {
            setSelectedState(newSelectedStat);
          }}
        />

        <StudyProgressChart
          label={selectedStat}
          data={isFirstTimeLoad ? undefined : studyProgressQuery.data!}
        />

        <StudySegmentsTables
          studySlug={studySlug}
          showLoader={isFirstTimeLoad}
        />
      </React.Fragment>
    </PageLayout>
  );
};

export default StudyPage;
