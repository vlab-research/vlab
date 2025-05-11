import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import useStudy from './hooks/useStudy';
import StudyProgressStats from './components/StudyProgressStats';
import StudyProgressChart from './components/StudyProgressChart';
import ParticipantsAcquiredPerSegmentTable from './components/ParticipantsAcquiredPerSegmentTable';
import RecruitmentStatsTable from './components/RecruitmentStatsTable';
import Tabs from './components/Tabs';
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

const TABS = [
  { id: 'participants', label: 'Participants per Segment' },
  { id: 'recruitment', label: 'Recruitment Statistics' },
];

const StudyPage = () => {
  const { studySlug } = useParams<{ studySlug: string }>();
  const study = useStudy(studySlug);
  const [selectedStat, setSelectedState] = useState('Current Participants');
  const [selectedTab, setSelectedTab] = useState(TABS[0].id);

  if (study.anyErrorDuringLoading) {
    return (
      <PageLayout title={''}>
        <ErrorPlaceholder
          message="Something went wrong while fetching the Study."
          onClickTryAgain={study.refetch}
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

        <div className="mt-8">
          <Tabs
            tabs={TABS}
            selectedTabId={selectedTab}
            onSelectTab={setSelectedTab}
          />

          {selectedTab === 'participants' ? (
            <ParticipantsAcquiredPerSegmentTable />
          ) : (
            <RecruitmentStatsTable data={study.recruitmentStats} />
          )}
        </div>
      </React.Fragment>
    </PageLayout>
  );
};

export default StudyPage;
