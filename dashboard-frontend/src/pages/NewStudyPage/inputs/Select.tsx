import React, { useCallback, useEffect, useState } from 'react';

const SelectInput = ({
  config,
  setCurrentConfig,
  formData,
  setFormData,
  ...props
}: any) => {
  const { id, name, label, options } = props;
  const { selector } = config;

  const [selectedOption, setSelectedOption] = useState({
    name: '',
    label: '',
  });

  const isCountryType = id === 'country';

  const handleChange = () => (e: any) => {
    const { value } = e.target;
    const findOption = options.findIndex(
      (option: any) => option.label === value
    );
    const option = options[findOption];
    setSelectedOption(option);
  };

  const findNestedConfig = useCallback(() => {
    const index = options.findIndex(
      (option: any) => option.name === selectedOption.name
    );
    return selector?.options[index];
  }, [options, selectedOption, selector]);

  useEffect(() => {
    selector && setCurrentConfig(findNestedConfig());
  }, [findNestedConfig, selector, setCurrentConfig]);

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
            value={selectedOption.label}
            onChange={handleChange()}
            data-testid={`new-study-${id}-input`}
            required
            className="mt-1 block w-full shadow-sm sm:text-sm rounded-md"
          >
            {!isCountryType && (
              <option value="">--Please choose an option--</option>
            )}
            {options.map((option: any) => (
              <option key={option.name} value={option.label}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>
    </React.Fragment>
  );
};

export default SelectInput;
