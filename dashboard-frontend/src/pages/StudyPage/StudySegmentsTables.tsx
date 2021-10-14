import React from 'react';
import StudySegmentsTable from './StudySegmentsTable';
import { formatNumber } from '../../helpers/numbers';

const StudySegmentsTables = () => (
  <React.Fragment>
    <StudySegmentsTable
      title="Summary per segment"
      testId="summary-per-segment-table"
      columnNames={['Name', '%Deviation', 'Budget', 'Spent']}
      getRowData={segmentProgress => ({
        id: segmentProgress.id,
        firstColumn: segmentProgress.name,
        secondColumn: formatNumber(segmentProgress.percentageDeviationFromGoal),
        thirdColumn: formatNumber(segmentProgress.currentBudget),
        fourthColumn: formatNumber(
          Number(
            (
              segmentProgress.currentParticipants *
              segmentProgress.currentPricePerParticipant
            ).toFixed(2)
          )
        ),
      })}
    />

    <StudySegmentsTable
      title="% Participants per segment"
      testId="percentage-participants-per-segment-table"
      columnNames={['Name', '%Desired', '%Current', '%Expected']}
      getRowData={segmentProgress => ({
        id: segmentProgress.id,
        firstColumn: segmentProgress.name,
        secondColumn: formatNumber(segmentProgress.desiredPercentage),
        thirdColumn: formatNumber(segmentProgress.currentPercentage),
        fourthColumn: formatNumber(segmentProgress.expectedPercentage),
      })}
    />

    <StudySegmentsTable
      title="Participants per segment"
      testId="participants-per-segment-table"
      columnNames={['Name', 'Desired', 'Current', 'Expected']}
      getRowData={segmentProgress => ({
        id: segmentProgress.id,
        firstColumn: segmentProgress.name,
        secondColumn: segmentProgress.desiredParticipants
          ? formatNumber(segmentProgress.desiredParticipants)
          : 'N/A',
        thirdColumn: formatNumber(segmentProgress.currentParticipants),
        fourthColumn: formatNumber(segmentProgress.expectedParticipants),
      })}
    />
  </React.Fragment>
);

export default StudySegmentsTables;
