import { classNames } from '../helpers/strings';

const ListItem = ({
  children,
  size = '300',
  className = '',
  testId,
  rounded = false,
}: {
  children: string;
  size?: '100' | '200' | '300' | '400' | '500';
  className?: string;
  testId?: string;
  rounded?: boolean;
  loading?: boolean;
  onClick?: () => void;
}) => {
  const classNamePerSize = {
    100: 'inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md shadow-sm text-white bg-gray-600 hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500',
    200: 'inline-flex items-center px-3.5 py-2 border border-transparent text-sm leading-4 font-medium rounded-md shadow-sm text-white bg-gray-600 hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500',
    300: 'inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-gray-600 hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500',
    400: 'inline-flex items-center px-5 py-2 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-gray-600 hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500',
    500: 'inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-gray-600 hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500',
  };

  return (
    <li
      data-testid={testId}
      className={classNames(
        classNamePerSize[size],
        rounded ? 'rounded-full' : '',
        className
      )}
    >
      <span className="relative flex items-center justify-center">
        <span className={classNames('flex items-center justify-center')}>
          {children}
        </span>
      </span>
    </li>
  );
};

export default ListItem;
