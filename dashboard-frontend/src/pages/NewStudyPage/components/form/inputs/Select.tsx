import { createNameFor } from '../../../../../helpers/strings';

const Select = ({ onChange, ...props }: any) => {
  const { id, name, label, options, value } = props;

  const eventHandler = (e: any) =>
    onChange({ type: e.type, value: e.target.value });

  interface SelectOption {
    name: string;
    label?: string;
    code?: string;
  }

  return (
    <div className="sm:my-4">
      {label && (
        <label htmlFor={id} className="block text-sm font-medium text-gray-700">
          {label}
        </label>
      )}
      <div className="relative">
        <select
          id={id}
          name={name}
          value={value && createNameFor(value)}
          required
          onChange={eventHandler}
          data-testid={`new-study-select-input-${id}`}
          className="w-4/5 mt-1 block shadow-sm sm:text-sm rounded-md"
        >
          {options.map((option: SelectOption, i: number) => (
            <option key={i} value={option.name}>
              {option.label || option.name}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};

export default Select;
