import React from 'react';
import { classNames } from '../../../helpers/strings';

const TextInput = ({ config, state, setState, ...props }: any) => {
  const { id, name, label, helperText } = props;
  const configKey = config[0];
  const value = state[configKey][id];

  const handleChange = () => (e: any) => {
    const { value } = e.target;
    setState((prevState: any) => ({
      [configKey]: { ...prevState[configKey], [id]: value },
    }));
  };

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
          <input
            {...props}
            id={id}
            name={name}
            value={value}
            required
            placeholder={helperText}
            onChange={handleChange()}
            data-testid={`new-study-${id}-input`}
            className={classNames(
              'mt-1 block w-full shadow-sm sm:text-sm rounded-md',
              props.errorOnCreate
                ? 'focus:ring-red-500 focus:border-red-500 border-red-300 text-red-900 pr-10'
                : 'focus:ring-indigo-500 focus:border-indigo-500 border-gray-300'
            )}
          />
        </div>
      </div>
    </React.Fragment>
  );
};

export default TextInput;
