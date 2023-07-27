import { Path } from 'react-hook-form';
import { createLabelFor } from '../../../helpers/strings';


interface SelectOption {
  value: string;
  label: string;
}


interface MultiSelectProps<T> {
  name: Path<T>;
  options: SelectOption[];
  handleMultiSelectChange: (selectedValues: string[], name: string) => void;
  handleChange: (e: any) => void;
  value: any;
  disabled?: boolean;
  required?: boolean;
  label?: string;
}

export type MultiSelectI<T = any> = React.FC<MultiSelectProps<T>>;

export const GenericMultiSelect: MultiSelectI = ({
  name,
  options,
  handleChange,
  value,
  disabled = false,
  required = true,
  label,
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
              value={option.name.toUpperCase()}
              className="px-4 py-2 text-gray-700 sm:text-sm rounded-md cursor-pointer hover:text-gray-900 hover:bg-gray-100 transition duration-300 ease-in-out focus:outline-none"
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
