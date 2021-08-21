import { classNames } from '../../helpers/strings';

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
}: {
  columnNames: string[];
  rows: {
    id: string;
    firstColumn: string;
    secondColumn: string;
    thirdColumn: string;
    fourthColumn: string;
  }[];
  pagination: PaginationProps;
}) => (
  <TableContainer pagination={pagination}>
    <thead className="bg-gray-50">
      <tr>
        {columnNames.map(columnName => (
          <TableHeaderCell key={columnName}>{columnName}</TableHeaderCell>
        ))}
      </tr>
    </thead>
    <tbody className="bg-white divide-y divide-gray-200">
      {rows.map(row => (
        <tr key={row.id}>
          <TableCell first>{row.firstColumn}</TableCell>
          <TableCell>{row.secondColumn}</TableCell>
          <TableCell>{row.thirdColumn}</TableCell>
          <TableCell>{row.fourthColumn}</TableCell>
        </tr>
      ))}
    </tbody>
  </TableContainer>
);

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
      {Array.from({ length: numRows }, (_, index) => (
        <tr key={index}>
          <TableCell first>&nbsp;</TableCell>
          <TableCell>&nbsp;</TableCell>
          <TableCell>&nbsp;</TableCell>
          <TableCell>&nbsp;</TableCell>
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
          <table className="min-w-full divide-y divide-gray-200">
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

const TableHeaderCell = ({ children }: { children: string }) => (
  <th
    scope="col"
    className="px-1 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
  >
    {children}
  </th>
);

const TableCell = ({
  first = false,
  children,
}: {
  first?: boolean;
  children: string;
}) => (
  <td
    className={classNames(
      'px-1 sm:px-6 py-4 text-sm',
      first ? 'font-medium text-gray-900' : 'whitespace-nowrap text-gray-500'
    )}
  >
    {children}
  </td>
);

export default Table;
