import React from 'react';

const SelectInput = ({ state, setstate, getId, ...props }: any) => {
  const isCountryType = props.id === 'country';

  const handleOnChange = (field: any) => (e: any) => {
    const { value } = e.target;
    setstate((prevState: any) => ({ ...prevState, [field]: value }));
  };

  const name = props.name;
  const value = state[name];

  getId(props.id);

  return (
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
            id={props.id}
            name={props.name}
            value={value}
            onChange={handleOnChange(name)}
            data-testid={`new-study-${props.id}-input`}
            required
            className="mt-1 block w-full shadow-sm sm:text-sm rounded-md"
          >
            {isCountryType ? (
              props.options.map((country: any) => (
                <option key={country.code} value={country.code}>
                  {country.name}
                </option>
              ))
            ) : (
              <>
                <option value="">--Please choose an option--</option>
                {props.options?.map((option: any) => (
                  <option key={option.name} value={option.name}>
                    {option.name}
                  </option>
                ))}
              </>
            )}
          </select>
        </div>
      </div>
    </React.Fragment>
  );
};

export default SelectInput;
