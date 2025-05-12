import { ArrowSmUpIcon, ArrowSmDownIcon } from '@heroicons/react/solid';
import { classNames, createSlugFor } from '../../../helpers/strings';

interface PaginationProps {
  from: number;
  to: number;
  total: number;
  previousButton: {
    disabled: boolean;
    onClick: () => void;
  };
  nextButton: {
    disabled: boolean;
    onClick: () => void;
  };
}

const Table = ({
  columnNames,
  rows,
  pagination,
  selectedColumn,
}: {
  columnNames: string[];
  rows: {
    id: string;
    values: string[];
  }[];
  pagination: PaginationProps;
  selectedColumn: {
    hasDescendingOrder: boolean;
    index: number;
    onChange: (newIndex: number) => void;
  };
}) => {
  return (
    <TableContainer pagination={pagination}>
      <thead className="bg-gray-50">
        <tr>
          {columnNames.map((columnName, index) => (
            <TableHeaderCell
              key={columnName}
              selected={selectedColumn.index === index}
              onClick={() => selectedColumn.onChange(index)}
              hasDescendingOrder={selectedColumn.hasDescendingOrder}
              first={index === 0}
            >
              {columnName}
            </TableHeaderCell>
          ))}
        </tr>
      </thead>
      <tbody className="bg-white divide-y divide-gray-200">
        {rows.map(({ id, values }) => (
          <tr key={id}>
            {values.map((cellValue, index) => (
              <TableCell
                first={index === 0}
                key={index}
                testId={createSlugFor(`${columnNames[index]}-column-value`)}
              >
                {cellValue}
              </TableCell>
            ))}
          </tr>
        ))}
      </tbody>
    </TableContainer>
  );
};

export const TableSkeleton = ({
  numRows,
  testId,
  numColumns = 4,
}: {
  numRows: number;
  testId?: string;
  numColumns?: number;
}) => (
  <TableContainer
    testId={testId}
    pagination={{
      from: 1,
      to: numRows,
      total: numRows,
      previousButton: {
        disabled: true,
        onClick: () => {},
      },
      nextButton: {
        disabled: true,
        onClick: () => {},
      },
    }}
  >
    <thead className="bg-gray-50">
      <tr>
        {Array.from({ length: numColumns }, (_, index) => (
          <TableHeaderCell key={index}>&nbsp;</TableHeaderCell>
        ))}
      </tr>
    </thead>
    <tbody className="bg-white divide-y divide-gray-200">
      {Array.from({ length: numRows }, (_, rowIndex) => (
        <tr key={rowIndex}>
          {Array.from({ length: numColumns }, (_, colIndex) => (
            <td
              key={colIndex}
              className={classNames(
                'px-1 sm:px-6 py-4 text-sm',
                colIndex === 0 ? 'font-medium text-gray-900' : 'whitespace-nowrap text-gray-500'
              )}
            >
              <div
                className="animate-pulse bg-gray-200 rounded h-4"
                style={{
                  animationFillMode: 'backwards',
                  animationDelay: `${150 * (rowIndex * numColumns + colIndex)}ms`,
                }}
              />
            </td>
          ))}
        </tr>
      ))}
    </tbody>
  </TableContainer>
);

const TableContainer = ({
  testId,
  children,
  pagination,
}: {
  testId?: string;
  children: React.ReactNode;
  pagination: PaginationProps;
}) => (
  <div className="flex flex-col" data-testid={testId}>
    <div className="-my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
      <div className="py-2 align-middle inline-block min-w-full sm:px-6 lg:px-8">
        <div className="shadow overflow-hidden border-b border-gray-200 rounded-lg">
          <table className="min-w-full w-full table-fixed divide-y divide-gray-200">
            {children}
          </table>
          <Pagination {...pagination} />
        </div>
      </div>
    </div>
  </div>
);

const Pagination = ({
  from,
  to,
  total,
  previousButton,
  nextButton,
}: PaginationProps) => (
  <nav
    className="bg-white px-2 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6"
    aria-label="Pagination"
  >
    <div className="block">
      <p className="text-sm text-gray-700">
        Showing <span className="font-medium">{from}</span> to{' '}
        <span className="font-medium">{to}</span> of{' '}
        <span className="font-medium">{total}</span> results
      </p>
    </div>
    <div className="flex-1 flex justify-end">
      <button
        className={classNames(
          'relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50',
          previousButton.disabled ? 'opacity-50 cursor-not-allowed' : ''
        )}
        disabled={previousButton.disabled}
        onClick={previousButton.disabled ? () => {} : previousButton.onClick}
      >
        Previous
      </button>
      <button
        className={classNames(
          'ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50',
          nextButton.disabled ? 'opacity-50 cursor-not-allowed' : ''
        )}
        disabled={nextButton.disabled}
        onClick={nextButton.disabled ? () => {} : nextButton.onClick}
      >
        Next
      </button>
    </div>
  </nav>
);

const TableHeaderCell = ({
  children,
  selected = false,
  hasDescendingOrder = false,
  first = false,
  onClick = () => {},
}: {
  children: string;
  selected?: boolean;
  hasDescendingOrder?: boolean;
  first?: boolean;
  onClick?: () => void;
}) => (
  <th
    scope="col"
    className={classNames(
      'px-1 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer select-none hover:text-indigo-600',
      selected ? 'text-indigo-600 ' : '',
      first ? 'w-40' : 'w-24'
    )}
    onClick={onClick}
  >
    <span className="relative">
      {children}

      <ArrowSmDownIcon
        className={classNames(
          'h-4 w-4 absolute -right-4 top-0',
          selected && hasDescendingOrder ? 'opacity-1' : 'opacity-0'
        )}
        aria-hidden="true"
        data-testid="selected-column-descending-indicator"
      />

      <ArrowSmUpIcon
        className={classNames(
          'h-4 w-4 absolute -right-4 top-0',
          selected && !hasDescendingOrder ? 'opacity-1' : 'opacity-0'
        )}
        aria-hidden="true"
        data-testid="selected-column-ascending-indicator"
      />
    </span>
  </th>
);

const TableCell = ({
  first = false,
  children,
  testId,
}: {
  first?: boolean;
  children: string;
  testId?: string;
}) => (
  <td
    className={classNames(
      'px-1 sm:px-6 py-4 text-sm',
      first ? 'font-medium text-gray-900' : 'whitespace-nowrap text-gray-500'
    )}
    data-testid={testId}
  >
    {children}
  </td>
);

export default Table;
