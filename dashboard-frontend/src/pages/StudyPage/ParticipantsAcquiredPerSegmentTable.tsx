import React from 'react';
import { useParams } from 'react-router-dom';
import Table, { TableSkeleton } from './Table';
import useStudy from '../../hooks/useStudy';
import { formatNumber, parseNumber } from '../../helpers/numbers';
import { StudySegmentProgressResource } from '../../types/study';

const segmentsPerPage = 10;

const ParticipantsAcquiredPerSegmentTable = () => {
  const params = useParams<{ studySlug: string }>();
  const study = useStudy(params.studySlug);
  const tableProps = useTableProps(study);

  if (study.isLoading) {
    return (
      <TableLayout>
        <TableSkeleton
          testId="participants-acquired-per-segment-table-skeleton"
          numRows={segmentsPerPage}
        />
      </TableLayout>
    );
  }

  return (
    <TableLayout testId="participants-acquired-per-segment-table">
      <Table {...tableProps} />
    </TableLayout>
  );
};
const TableLayout = ({
  children,
  testId,
}: {
  children: React.ReactNode;
  testId?: string;
}) => (
  <div className="pt-5 sm:pt-6 lg:pt-10" data-testid={testId}>
    <h3 className="text-lg leading-6 font-medium text-gray-900">
      Participants acquired per segment
    </h3>
    <div className="pt-4">{children}</div>
  </div>
);

type SelectedColumn = {
  index: number;
  onChange: (newIndex: number) => void;
  hasDescendingOrder: boolean;
};

const useTableProps = (study: ReturnType<typeof useStudy>) => {
  const [selectedColumnIndex, setSelectedColumnIndex] = React.useState(3);
  const [hasDescendingOrder, setHasDescendingOrder] = React.useState(false);

  const [currentPage, setCurrentPage] = React.useState(0);
  const startIndex = currentPage * segmentsPerPage;
  const endIndex = startIndex + segmentsPerPage;
  const numberItems = study.currentSegmentsProgress.length;

  const selectedColumn: SelectedColumn = {
    index: selectedColumnIndex,
    onChange: newIndex => {
      const isSelectedColumn = selectedColumnIndex === newIndex;
      if (isSelectedColumn) {
        setHasDescendingOrder(currentState => !currentState);
      } else {
        setSelectedColumnIndex(newIndex);
        setHasDescendingOrder(true);
      }
    },
    hasDescendingOrder,
  };

  const visibleRows = getFormattedSortedRowsFor(
    study.currentSegmentsProgress,
    selectedColumn
  ).slice(startIndex, endIndex);

  const pagination = {
    from: numberItems > 0 ? startIndex + 1 : 0,
    to: Math.min(endIndex, numberItems),
    total: numberItems,
    previousButton: {
      disabled: currentPage === 0,
      onClick: () => {
        setCurrentPage(currentPage => currentPage - 1);
      },
    },
    nextButton: {
      disabled: endIndex >= numberItems,
      onClick: () => {
        setCurrentPage(currentPage => currentPage + 1);
      },
    },
  };

  return {
    selectedColumn,
    rows: visibleRows,
    pagination,
    columnNames: [
      'Name',
      '%Deviation',
      '%Desired',
      '%Current',
      '%Expected',
      'Current',
      'Expected',
      'Budget',
      'Price',
    ],
  };
};

const getFormattedSortedRowsFor = (
  currentSegmentsProgress: StudySegmentProgressResource[],
  selectedColumn: SelectedColumn
) => {
  const formattedRows = currentSegmentsProgress.map(segmentProgress => ({
    id: segmentProgress.id,
    values: [
      segmentProgress.name,
      formatNumber(segmentProgress.percentageDeviationFromGoal),
      formatNumber(segmentProgress.desiredPercentage),
      formatNumber(segmentProgress.currentPercentage),
      formatNumber(segmentProgress.expectedPercentage),
      formatNumber(segmentProgress.currentParticipants),
      formatNumber(segmentProgress.expectedParticipants),
      formatNumber(segmentProgress.currentBudget),
      formatNumber(segmentProgress.currentPricePerParticipant),
    ],
  }));

  return formattedRows.sort((a, b) => {
    if (selectedColumn.index === 0 && selectedColumn.hasDescendingOrder) {
      return b.values[selectedColumn.index].localeCompare(
        a.values[selectedColumn.index]
      );
    }

    if (selectedColumn.index === 0 && !selectedColumn.hasDescendingOrder) {
      return a.values[selectedColumn.index].localeCompare(
        b.values[selectedColumn.index]
      );
    }

    if (selectedColumn.hasDescendingOrder) {
      return (
        parseNumber(b.values[selectedColumn.index]) -
        parseNumber(a.values[selectedColumn.index])
      );
    }

    return (
      parseNumber(a.values[selectedColumn.index]) -
      parseNumber(b.values[selectedColumn.index])
    );
  });
};

export default ParticipantsAcquiredPerSegmentTable;
