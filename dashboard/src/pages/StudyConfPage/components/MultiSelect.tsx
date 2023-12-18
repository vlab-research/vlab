import { Path } from 'react-hook-form';


interface SelectOption {
  value: string;
  label: string;
}


interface SelectOption {
  value: string;
  label: string;
}


interface MultiSelectProps<T> {
  name: Path<T>;
  options: SelectOption[];
  handleMultiSelectChange: (selectedValues: string[], name: string) => void;
  value: string[];
  label: string;
}

export type MultiSelectI<T = any> = React.FC<MultiSelectProps<T>>

export const GenericMultiSelect: MultiSelectI = ({
  name,
  options,
  handleMultiSelectChange,
  value,
  label,
}) => {
  const onChange = (e: any) => {
    const selected = Array.from(e.target.selectedOptions).map(
      (option: any) => option.value
    );
    handleMultiSelectChange(selected, name);
  };

  return (
    <div className="sm:my-4">
      <label className="my-2 block text-sm font-medium text-gray-700">
        {label}
      </label>
      <select
        multiple
        value={value}
        onChange={onChange}
        className="w-4/5 block shadow-sm sm:text-sm rounded-md"
      >
        {options.map((option: SelectOption, i: number) => (
          <option
            key={i}
            value={option.value}
            className="px-4 py-2 text-gray-700 sm:text-sm rounded-md cursor-pointer hover:text-gray-900 hover:bg-gray-100 transition duration-300 ease-in-out focus:outline-none"
          >
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
};
