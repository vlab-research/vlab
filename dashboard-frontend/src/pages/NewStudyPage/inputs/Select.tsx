import { Fragment } from 'react';

const Select = ({ selectedOption, setSelectedOption, ...props }: any) => {
  const { id, name, label, options, defaultValue } = props;

  // const [selectedOption, setSelectedOption] = useState({
  //   name: '',
  //   label: defaultValue,
  // });

  // console.log(selectedOption);

  const handleChange = () => (e: any) => {
    const { value } = e.target;
    const findOption = options.findIndex(
      (option: any) => option.label === value
    );
    const option = options[findOption];
    setSelectedOption(option);
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
          <select
            {...props}
            id={id}
            name={name}
            value={selectedOption?.label}
            onChange={handleChange()}
            data-testid={`new-study-${id}-input`}
            required
            className="mt-1 block w-full shadow-sm sm:text-sm rounded-md"
          >
            {defaultValue && <option value="">{defaultValue}</option>}
            {options.map((option: any) => (
              <option key={option.name} value={option.label}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>
    </Fragment>
  );
};

export default Select;
