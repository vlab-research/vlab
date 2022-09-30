import React from 'react';
import { classNames } from '../../helpers/strings';

const TextInput = ({ ...props }, errorMessage: string) => (
  <React.Fragment>
    <div className="sm:my-4">
      {props.label ? (
        <label
          htmlFor={props.id}
          className="block text-sm font-medium text-gray-700"
        >
          {props.label}
        </label>
      ) : null}

      <div className="relative">
        <input
          {...props}
          data-testid={`new-study-${props.id}-input`}
          className={classNames(
            'mt-1 block w-full shadow-sm sm:text-sm rounded-md'
            // errorMessage
            //   ? 'focus:ring-red-500 focus:border-red-500 border-red-300 text-red-900 pr-10'
            //   : 'focus:ring-indigo-500 focus:border-indigo-500 border-gray-300'
          )}
        />
      </div>
    </div>
  </React.Fragment>
);

export default TextInput;
