import React from 'react';
import { classNames } from '../../helpers/strings';
import countries from '../../fixtures/countries.json';

const Dropdown = ({ ...props }, errorMessage: string) => (
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
        <select
          {...props}
          name={props.name}
          id={props.id}
          data-testid={`new-study-${props.id}-input`}
          className={classNames(
            'mt-1 block w-full shadow-sm sm:text-sm rounded-md'
            // errorMessage
            //   ? 'focus:ring-red-500 focus:border-red-500 border-red-300 text-red-900 pr-10'
            //   : 'focus:ring-indigo-500 focus:border-indigo-500 border-gray-300'
          )}
        >
          {countries.map(country => (
            <option key={country.code}>{country.name}</option>
          ))}
        </select>
      </div>
    </div>
  </React.Fragment>
);

export default Dropdown;
