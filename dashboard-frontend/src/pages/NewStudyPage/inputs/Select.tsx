import React from 'react';

const SelectInput = ({ config, state, setState, ...props }: any) => {
  const configKey: string = config[0];
  const isCountryType = props.id === 'country';

  console.log(config);

  const handleChange = () => (e: any) => {
    const { value } = e.target;
    setState((prevState: any) => ({
      ...prevState,
      [configKey]: { ...prevState[configKey], [props.id]: value },
    }));
  };

  const { id, name } = props;
  const value: string = state[name];

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
            id={`${configKey}_${id}`}
            name={`${configKey}_${name}`}
            value={value}
            onChange={handleChange()}
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
