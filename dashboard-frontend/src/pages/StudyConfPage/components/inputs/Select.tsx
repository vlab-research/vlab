const Select = ({ onChange, ...props }: any) => {
  const { id, name, label, options } = props;

  const handleChange = (e: any) => onChange(e);

  interface SelectOption {
    name: string;
    label?: string;
    code?: string;
  }

  return (
    <>
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
            id={id}
            name={name}
            required
            onChange={handleChange}
            data-testid={`new-study-select-input-${id}`}
            className="mt-1 block w-full shadow-sm sm:text-sm rounded-md"
          >
            {options.map((option: SelectOption, i: number) => (
              <option key={i} value={option.name}>
                {option.label || option.name}
              </option>
            ))}
          </select>
        </div>
      </div>
    </>
  );
};

export default Select;
