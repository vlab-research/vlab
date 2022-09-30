import React from 'react';
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
          required
          className="mt-1 block w-full shadow-sm sm:text-sm rounded-md"
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
