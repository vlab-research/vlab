import React, { ChangeEventHandler } from 'react';
import { classNames } from '../../helpers/strings';

const InputSecret = ({
  error,
  handleChange,
  index,
  clientId,
  clientSecret,
}: {
  index: number;
  error: string | undefined;
  handleChange: ChangeEventHandler;
  clientId: string;
  clientSecret: string;
}) => (
  <React.Fragment>
    <div className="flex flex-col mb-4">
      <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-gray-300">
        Client ID
      </label>
      <input
        id="clientId"
        name="clientId"
        type="text"
        className={classNames(
          'block w-full shadow-sm sm:text-sm rounded-md',
          error
            ? 'focus:ring-red-500 focus:border-red-500 border-red-300 text-red-900 pr-10'
            : 'focus:ring-indigo-500 focus:border-indigo-500  border-gray-300'
        )}
        data-testid={`input-client-id-${index}`}
        placeholder="Enter token"
        onChange={handleChange}
        value={clientId}
        required
      />
    </div>
    <div className="flex flex-col mb-4">
      <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-gray-300">
        Client secret
      </label>
      <input
        id="clientSecret"
        name="clientSecret"
        type="text"
        className={classNames(
          'block w-full shadow-sm sm:text-sm rounded-md',
          error
            ? 'focus:ring-red-500 focus:border-red-500 border-red-300 text-red-900 pr-10'
            : 'focus:ring-indigo-500 focus:border-indigo-500  border-gray-300'
        )}
        data-testid={`input-client-secret-${index}`}
        placeholder="Enter token"
        onChange={handleChange}
        value={clientSecret}
        required
      />
    </div>
  </React.Fragment>
);

export default InputSecret;
