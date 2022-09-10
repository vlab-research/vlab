import { ExclamationCircleIcon } from '@heroicons/react/solid';
import React, { ChangeEventHandler } from 'react';
import { classNames } from '../../helpers/strings';

const InputToken = ({
  errorMessage,
  handleChange,
  index,
  token,
}: {
  index: number;
  errorMessage?: string;
  handleChange: ChangeEventHandler;
  token: string;
}) => (
  <React.Fragment>
    <div className="flex flex-col mb-4">
      <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-gray-300">
        Token
      </label>
      <input
        id="token"
        name="token"
        type="text"
        className={classNames(
          'block w-full shadow-sm sm:text-sm rounded-md',
          errorMessage
            ? 'focus:ring-red-500 focus:border-red-500 border-red-300 text-red-900 pr-10'
            : 'focus:ring-indigo-500 focus:border-indigo-500  border-gray-300'
        )}
        data-testid={`input-token-${index}`}
        placeholder="Enter token"
        onChange={handleChange}
        value={token}
      />
      {errorMessage && (
        <div className="absolute pointer-events-none inset-y-0 right-0 pr-3 flex items-center">
          <ExclamationCircleIcon
            className="h-5 w-5 text-red-500"
            aria-hidden="true"
          />
        </div>
      )}
    </div>
  </React.Fragment>
);

export default InputToken;
