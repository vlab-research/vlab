import React, { ChangeEventHandler } from 'react';
import { classNames } from '../../helpers/strings';

const InputToken = ({
  error,
  handleChange,
  index,
  token,
}: {
  index: number;
  error: string | undefined;
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
          error
            ? 'focus:ring-red-500 focus:border-red-500 border-red-300 text-red-900 pr-10'
            : 'focus:ring-indigo-500 focus:border-indigo-500  border-gray-300'
        )}
        data-testid={`input-token-${index}`}
        placeholder="Enter token"
        onChange={handleChange}
        value={token}
        required
      />
    </div>
  </React.Fragment>
);

export default InputToken;
