import * as icons from '@heroicons/react/solid';
import { classNames } from '../helpers/strings';

const SecondaryButton = ({
  children,
  size = '300',
  type = 'button',
  className = '',
  testId,
  rounded = false,
  icon,
  loading = false,
  onClick = () => {},
}: {
  children: string;
  size?: '100' | '200' | '300' | '400' | '500';
  type?: 'button' | 'submit';
  className?: string;
  testId?: string;
  rounded?: boolean;
  icon?: keyof typeof icons;
  loading?: boolean;
  onClick?: () => void;
}) => {
  const classNamePerSize = {
    100: 'inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md shadow-sm text-white bg-gray-500 hover:bg-gray-600 focus:outline-none',
    200: 'inline-flex items-center px-3.5 py-2 border border-transparent text-sm leading-4 font-medium rounded-md shadow-sm text-white bg-gray-500 hover:bg-indigo-600 focus:outline-none',
    300: 'inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-gray-500 hover:bg-gray-600 focus:outline-none',
    400: 'inline-flex items-center px-5 py-2 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-gray-500 hover:bg-gray-600 focus:outline-none',
    500: 'inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-gray-500 hover:bg-gray-600 focus:outline-none',
  };

  const iconClassNamePerSize = {
    100: 'h-4 w-4',
    200: 'h-4 w-4',
    300: 'h-5 w-5',
    400: 'h-5 w-5',
    500: 'h-5 w-5',
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
      <span className="flex items-center justify-center">
        {icon && <Icon name={icon} className={iconClassNamePerSize[size]} />}
        {children}
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

export default SecondaryButton;