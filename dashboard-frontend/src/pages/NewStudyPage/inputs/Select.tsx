import React from 'react';

const SelectInput = ({ config, state, setState, ...props }: any) => {
  const { id, name, label, options } = props;
  const configKey = config[0];
  const { type } = config[1];
  const value = state[configKey][id];
  const isCountryType = props.id === 'country';

  const handleChange = () => (e: any) => {
    const { value } = e.target;
    setState((prevState: any) => ({
      [configKey]: { ...prevState[configKey], [id]: value },
    }));
  };

  const isConfigObject = type === 'config-object' ? true : false;

  return (
    <React.Fragment>
      <div className="sm:my-4">
        {label && (
          <label
            htmlFor={id}
            className="block text-sm font-medium text-gray-700"
          >
            {label}
          </label>
        )}
        <div className="relative">
          <select
            {...props}
            id={id}
            name={name}
            value={value}
            onChange={handleChange()}
            data-testid={`new-study-${id}-input`}
            required
            className="mt-1 block w-full shadow-sm sm:text-sm rounded-md"
          >
            {isCountryType ? (
              options.map((country: any) => (
                <option key={country.code} value={country.code}>
                  {country.name}
                </option>
              ))
            ) : (
              <>
                <option value="">--Please choose an option--</option>
                {options?.map((option: any, index: number) => (
                  <option key={option[index]} value={option[index]}>
                    {isConfigObject ? option.label : option.title}
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
