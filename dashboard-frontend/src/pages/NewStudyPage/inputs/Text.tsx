import React from 'react';
import { classNames } from '../../../helpers/strings';

const TextInput = ({ config, state, setState, ...props }: any) => {
  const configKey: string = config[0];

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
          <input
            {...props}
            id={`${configKey}_${id}`}
            name={`${configKey}_${name}`}
            value={value}
            required
            placeholder={props.helpertext}
            onChange={handleChange()}
            data-testid={`new-study-${props.id}-input`}
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
