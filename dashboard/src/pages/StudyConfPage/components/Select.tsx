import { Path } from 'react-hook-form';
import { createLabelFor } from '../../../helpers/strings';

interface SelectProps<T> {
  name: Path<T>;
  options: { name: string; label: string }[] | any[];
  handleChange: (e: any) => void;
  value: any;
  disabled?: boolean;
  required?: boolean;
  label?: string;
  toUpperCase?: boolean;
}

export type SelectI<T = any> = React.FC<SelectProps<T>>;

export const GenericSelect: SelectI = ({
  name,
  options,
  handleChange,
  value,
  disabled = false,
  required = true,
  label,
  toUpperCase = false,
  ...props
}) => {
  return (
    <div className="sm:my-4">
      <label className="my-2 block text-sm font-medium text-gray-700">
        {label ? label : createLabelFor(name)}
      </label>
      <div className="flex flex-row items-center">
        <select
          name={name}
          value={value}
          onChange={e => handleChange(e)}
          className="w-4/5 mt-1 block shadow-sm sm:text-sm rounded-md"
          {...props}
        >
          {options.map((option: { name: string; label: string }, i: number) => (
            <option
              key={i}
              value={toUpperCase ? option.name.toUpperCase() : option.name}
            >
              {option.label || option.name}
            </option>
          ))}
        </select>
        {required === false && (
          <span className="ml-4 italic text-gray-700 text-sm">Optional</span>
        )}
      </div>
    </div>
  );
};
