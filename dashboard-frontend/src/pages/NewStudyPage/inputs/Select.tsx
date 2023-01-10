import { Fragment, useState } from 'react';
import PrimaryButton from '../../../components/PrimaryButton';

const Select = ({ onChange, ...props }: any) => {
  const { id, name, label, options, defaultValue, call_to_action } = props;

  const [selectedOption, setSelectedOption] = useState('');

  const handleChange = (e: any) => {
    const { value } = e.target;
    setSelectedOption(value);
    onChange(value);
  };

  const handleClick = () => {
    console.log('saved');
  };

  return (
    <Fragment>
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
            defaultValue={selectedOption}
            required
            onChange={handleChange}
            data-testid={`new-study-${id}-input`}
            className="mt-1 block w-full shadow-sm sm:text-sm rounded-md"
          >
            {defaultValue && <option defaultValue="">{defaultValue}</option>}
            {options.map((option: any) => (
              <option key={option.name} value={option.label || option.name}>
                {option.label || option.name}
              </option>
            ))}
          </select>
        </div>
      </div>
      {call_to_action && (
        <PrimaryButton onClick={() => handleClick()}>
          {call_to_action}
        </PrimaryButton>
      )}
    </Fragment>
  );
};

export default Select;
