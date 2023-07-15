import * as icons from '@heroicons/react/solid';
import { classNames } from '../helpers/strings';
import LoadingSpinner from './LoadingSpinner';

const PrimaryButton = ({
  children,
  size = '300',
  type = 'button',
  className = '',
  testId,
  rounded = false,
  leftIcon,
  loading = false,
  onClick = () => {},
}: {
  children: string;
  size?: '100' | '200' | '300' | '400' | '500';
  type?: 'button' | 'submit';
  className?: string;
  testId?: string;
  rounded?: boolean;
  leftIcon?: keyof typeof icons;
  loading?: boolean;
  onClick?: (e: any) => void;
}) => {
  const classNamePerSize = {
    100: 'inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 transition duration-300 ease-in-out focus:outline-none',
    200: 'inline-flex items-center px-3.5 py-2 border border-transparent text-sm leading-4 font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 transition duration-300 ease-in-out focus:outline-none',
    300: 'inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 transition duration-300 ease-in-out focus:outline-none',
    400: 'inline-flex items-center px-5 py-2 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 transition duration-300 ease-in-out focus:outline-none',
    500: 'inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 transition duration-300 ease-in-out focus:outline-none',
  };

  const iconClassNamePerSize = {
    100: '-ml-0.5 mr-2 h-4 w-4',
    200: '-ml-0.5 mr-2 h-4 w-4',
    300: '-ml-1 mr-2 h-5 w-5',
    400: '-ml-1 mr-3 h-5 w-5',
    500: '-ml-1 mr-3 h-5 w-5',
  };

  return (
    <button
      data-testid={testId}
      type={type}
      onClick={onClick}
      disabled={loading}
      className={classNames(
        classNamePerSize[size],
        rounded ? 'rounded-full' : '',
        className
      )}
    >
      <span className="relative flex items-center justify-center">
        <span
          className={classNames(
            'flex items-center justify-center',
            loading ? 'opacity-0' : 'opacity-1'
          )}
        >
          {leftIcon && (
            <Icon name={leftIcon} className={iconClassNamePerSize[size]} />
          )}
          {children}
        </span>
        {loading && (
          <span className="absolute">
            <LoadingSpinner />
          </span>
        )}
      </span>
    </button>
  );
};

const Icon = ({
  name,
  className,
}: {
  name: keyof typeof icons;
  className?: string;
}) => {
  const IconComponent = icons[name];

  return <IconComponent className={className} aria-hidden="true" />;
};

export default PrimaryButton;
