import React from 'react';
import Table, { TableSkeleton } from './Table';
import useStudySegmentsProgressQuery, {
  segmentsProgressPerPage,
} from './useStudySegmentsProgressQuery';
import { lastValue } from '../../helpers/arrays';
import { StudySegmentProgressResource } from '../../types/study';

const StudySegmentsTable = ({
  testId,
  loaderTestId,
  showLoader,
  studySlug,
  title,
  columnNames,
  getRowData,
}: {
  testId?: string;
  loaderTestId?: string;
  showLoader: boolean;
  studySlug: string;
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
  const [cursors, setCursors] = React.useState<Array<string | null>>([null]);
  const currentCursor = lastValue(cursors);
  const query = useStudySegmentsProgressQuery(studySlug, currentCursor);

  return (
    <div className="pt-5 sm:pt-6 lg:pt-10" data-testid={testId}>
      <h3 className="text-lg leading-6 font-medium text-gray-900">{title}</h3>
      <div className="pt-4">
        {!showLoader && query?.resolvedData?.data ? (
          <Table
            columnNames={columnNames}
            rows={query.resolvedData.data.map(getRowData)}
            pagination={{
              from: query.resolvedData.pagination.from,
              to: query.resolvedData.pagination.to,
              total: query.resolvedData.pagination.total,
              previousButton: {
                disabled: currentCursor === null,
                onClick: () => {
                  const newCursors = cursors.slice(0, cursors.length - 1);
                  setCursors(newCursors);
                },
              },
              nextButton: {
                disabled: !query.latestData?.pagination.nextCursor,
                onClick: () => {
                  if (query.latestData?.pagination.nextCursor) {
                    setCursors([
                      ...cursors,
                      query.latestData.pagination.nextCursor,
                    ]);
                  }
                },
              },
            }}
          />
        ) : (
          <TableSkeleton
            testId={loaderTestId}
            numRows={segmentsProgressPerPage}
          />
        )}
      </div>
    </div>
  );
};

export default StudySegmentsTable;
