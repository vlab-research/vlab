import { useState, Fragment } from 'react';
import { classNames } from '../../../helpers/strings';

const Text = ({ onChange, ...props }: any) => {
  const { id, name, label, helper_text, errorOnCreate } = props;

  const [inputText, setInputText] = useState('');

  const handleChange = (e: any) => {
    const { value } = e.target;
    setInputText(value);
    onChange(value);
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
          <input
            {...props}
            id={id}
            name={name}
            value={inputText}
            required
            placeholder={helper_text}
            onChange={handleChange}
            data-testid={`new-study-${id}-input`}
            className={classNames(
              'mt-1 block w-full shadow-sm sm:text-sm rounded-md',
              errorOnCreate
                ? 'focus:ring-red-500 focus:border-red-500 border-red-300 text-red-900 pr-10'
                : 'focus:ring-indigo-500 focus:border-indigo-500 border-gray-300'
            )}
          />
        </div>
      </div>
    </Fragment>
  );
};

export default Text;
