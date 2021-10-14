import React from 'react';
import { useParams } from 'react-router-dom';
import Table, { TableSkeleton } from './Table';
import useStudy from './useStudy';
import { StudySegmentProgressResource } from '../../types/study';

const segmentsProgressPerPage = 7;

const StudySegmentsTable = ({
  testId,
  title,
  columnNames,
  getRowData,
}: {
  testId?: string;
  title: string;
  columnNames: string[];
  getRowData: (studySegmentProgress: StudySegmentProgressResource) => {
    id: string;
    firstColumn: string;
    secondColumn: string;
    thirdColumn: string;
    fourthColumn: string;
  };
}) => {
  const params = useParams<{ studySlug: string }>();
  const study = useStudy(params.studySlug);
  const [currentPage, setCurrentPage] = React.useState(0);

  if (study.isLoading) {
    return (
      <TableLayout title={title}>
        <TableSkeleton
          testId="study-segment-table-skeleton"
          numRows={segmentsProgressPerPage}
        />
      </TableLayout>
    );
  }

  const startIndex = currentPage * segmentsProgressPerPage;
  const endIndex = startIndex + segmentsProgressPerPage;
  const numberItems = study.currentSegmentsProgress.length;

  const visibleRows = study.currentSegmentsProgress
    .slice(startIndex, endIndex)
    .map(getRowData);

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
      disabled: endIndex > numberItems,
      onClick: () => {
        setCurrentPage(currentPage => currentPage + 1);
      },
    },
  };

  return (
    <TableLayout title={title} testId={testId}>
      <Table
        columnNames={columnNames}
        rows={visibleRows}
        pagination={pagination}
      />
    </TableLayout>
  );
};
const TableLayout = ({
  title,
  children,
  testId,
}: {
  title: string;
  children: React.ReactNode;
  testId?: string;
}) => (
  <div className="pt-5 sm:pt-6 lg:pt-10" data-testid={testId}>
    <h3 className="text-lg leading-6 font-medium text-gray-900">{title}</h3>
    <div className="pt-4">{children}</div>
  </div>
);

export default StudySegmentsTable;
