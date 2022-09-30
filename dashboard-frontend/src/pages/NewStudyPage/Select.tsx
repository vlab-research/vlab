import React from 'react';

const Select = ({ ...props }, errorMessage: string) => (
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
          <option value="">--Please choose an option--</option>
          <option value="dog">Dog</option>
          <option value="cat">Cat</option>
          <option value="hamster">Hamster</option>
          <option value="parrot">Parrot</option>
          <option value="spider">Spider</option>
          <option value="goldfish">Goldfish</option>
        </select>
      </div>
    </div>
  </React.Fragment>
);

export default Select;
