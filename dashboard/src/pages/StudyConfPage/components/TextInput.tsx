import { Path } from 'react-hook-form';
import { classNames, createLabelFor } from '../../../helpers/strings';

interface TextProps<T> {
  name: Path<T>;
  handleChange: (e: any) => void;
  autoComplete?: string;
  placeholder: string;
  value: any;
  type?: string;
  disabled?: boolean;
  required?: boolean;
}

export type TextInputI<T = any> = React.FC<TextProps<T>>;

export const GenericTextInput: TextInputI = ({
  name,
  handleChange,
  autoComplete = 'on',
  placeholder,
  value,
  type = "text",
  disabled = false,
  required = true,
  ...props
}) => {

  return (
    <div className="sm:my-4">
      <label className="my-2 block text-sm font-medium text-gray-700">
        {createLabelFor(name)}
      </label>
      <div className="flex flex-row items-center">
        <input
          name={name}
          type={type}
          autoComplete={autoComplete}
          placeholder={placeholder}
          value={value}
          required={required}
          disabled={disabled}
          {...props}
          onChange={handleChange}
          className={classNames(
            'block w-4/5 shadow-sm sm:text-sm rounded-md',
            disabled ? 'opacity-50 cursor-not-allowed' : ''
          )}
        />
        {required === false && (
          <span className="ml-4 italic text-gray-700 text-sm">Optional</span>
        )}
      </div>
    </div>
  );
};
