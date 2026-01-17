import Stats, { StatsSkeleton } from './Stats';
import { StudyProgressResource } from '../../../types/study';
import { formatNumber, formatCurrency } from '../../../helpers/numbers';

const StudyProgressStats = ({
  currentProgress,
  totalSpent,
  avgCostPerParticipant,
  selectedStat,
  onSelectStat,
  isLoading,
}: {
  currentProgress?: StudyProgressResource;
  totalSpent: number;
  avgCostPerParticipant: number;
  selectedStat: string;
  onSelectStat: (selectedStat: string) => void;
  isLoading?: boolean;
}) => {
  if (isLoading || !currentProgress) {
    return (
      <StatsSkeleton
        statTestId="study-current-progress-card-skeleton"
        statNames={[
          'Current Participants',
          'Expected Participants',
          'Total Spent',
          'Avg Cost Per Participant',
        ]}
        selectedStat="Current Participants"
      />
    );
  }

  return (
    <Stats
      testId="study-page-stats"
      selectedStat={selectedStat}
      onSelectStat={onSelectStat}
      stats={[
        {
          name: 'Current Participants',
          stat: formatNumber(currentProgress.currentParticipants),
        },
        {
          name: 'Expected Participants',
          stat: formatNumber(currentProgress.expectedParticipants),
        },
        {
          name: 'Total Spent',
          stat: formatCurrency(totalSpent),
        },
        {
          name: 'Avg Cost Per Participant',
          stat: avgCostPerParticipant > 0
            ? formatCurrency(avgCostPerParticipant)
            : '-',
        },
      ]}
    />
  );
};

export default StudyProgressStats;
