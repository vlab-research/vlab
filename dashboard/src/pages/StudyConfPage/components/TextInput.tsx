import { Path } from 'react-hook-form';
import { classNames, createLabelFor } from '../../../helpers/strings';

interface TextProps<T> {
  name: Path<T>;
  type?: string;
  handleChange: (e: any) => void;
  autoComplete?: string;
  placeholder: string;
  value: any;
  disabled?: boolean;
  required?: boolean;
}

export type TextInputI<T = any> = React.FC<TextProps<T>>

export const GenericTextInput: TextInputI = ({
  name,
  type,
  handleChange,
  autoComplete,
  placeholder,
  value,
  disabled = false,
  required = true,
  ...props
}) => (
  <div className="sm:my-4">
    <label className="my-2 block text-sm font-medium text-gray-700">
      {createLabelFor(name)}
    </label>
    <input
      name={name}
      type={type}
      autoComplete={autoComplete}
      placeholder={placeholder}
      value={value}
      required={required}
      disabled={disabled}
      {...props}
      onChange={e => handleChange(e)}
      className={classNames(
        "block w-2/5 shadow-sm sm:text-sm rounded-md",
        disabled ? 'opacity-50 cursor-not-allowed' : ''
      )}

    />
  </div>
);
