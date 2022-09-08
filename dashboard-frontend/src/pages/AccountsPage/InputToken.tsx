import { ExclamationCircleIcon } from '@heroicons/react/solid';
import React, { ChangeEventHandler } from 'react';
import { classNames } from '../../helpers/strings';
import { TokenAccountResource } from '../../types/account';

const InputToken = ({
  existingCredentials,
  credentials,
  errorMessage,
  handleChange,
  index,
}: {
  existingCredentials: TokenAccountResource | null;
  credentials: any;
  index: number;
  errorMessage?: string;
  handleChange: ChangeEventHandler;
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
        value={
          existingCredentials?.credentials
            ? existingCredentials.credentials.token
            : credentials.token
        }
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
    <p className="mt-2 text-sm text-red-600 h-1">{errorMessage}</p>
  </React.Fragment>
);

export default InputToken;
