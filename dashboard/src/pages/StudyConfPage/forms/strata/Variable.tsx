import { Path } from 'react-hook-form';
import { classNames, createLabelFor } from '../../../../helpers/strings';
import { useState } from 'react';
import AddButton from '../../../../components/AddButton';
import Level from './Level';
import DeleteButton from '../../../../components/DeleteButton';

export interface FormData {
  name: string;
  properties: string[];
  levels: any[];
}

interface TextProps {
  name: Path<FormData>;
  type?: string;
  handleChange: (e: any) => void;
  autoComplete: string;
  placeholder: string;
  required: boolean;
  value: any;
}
const TextInput: React.FC<TextProps> = ({
  name,
  type,
  handleChange,
  autoComplete,
  placeholder,
  value,
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
      required
      onChange={e => handleChange(e)}
      className="block w-2/5 shadow-sm sm:text-sm rounded-md"
    />
  </div>
);

interface MultiSelectProps {
  name: Path<FormData>;
  options: SelectOption[];
  handleMultiSelectChange: (selectedValues: string[], name: string) => void;
  value: string[];
  label: string;
}

interface SelectOption {
  name: string;
  label: string;
}

const MultiSelect: React.FC<MultiSelectProps> = ({
  name,
  options,
  handleMultiSelectChange,
  value,
  label,
}: MultiSelectProps) => {
  const [selectedValues, setSelectedValues] = useState<string[]>(
    value ? value : []
  );

  const onChange = (e: any) => {
    const selected = Array.from(e.target.selectedOptions).map(
      (option: any) => option.value
    );

    setSelectedValues(selected);

    handleMultiSelectChange(selected, name);
  };

  return (
    <div className="sm:my-4">
      <label className="my-2 block text-sm font-medium text-gray-700">
        {label}
      </label>
      <select
        multiple
        value={selectedValues}
        onChange={onChange}
        className="w-4/5 block shadow-sm sm:text-sm rounded-md"
      >
        {options.map((option: SelectOption, i: number) => (
          <>
            <option
              key={i}
              value={option.name}
              className="px-4 py-2 text-gray-700 sm:text-sm rounded-md cursor-pointer hover:text-gray-900 hover:bg-gray-100 transition duration-300 ease-in-out focus:outline-none"
            >
              {option.label}
            </option>
          </>
        ))}
      </select>
    </div>
  );
};

interface Props {
  data: any;
  formData: any[];
  index: number;
  updateFormData: (d: any, index: number) => void;
}

const Variable: React.FC<Props> = ({
  data,
  formData,
  index,
  updateFormData,
}: Props) => {
  const initialState = [{ name: '', properties: [], levels: [] }];

  const [levels, setLevels] = useState<any[]>(
    data.levels
      ? data.levels
      : [
          {
            name: 'foo',
            adset: [{ name: 'adset_1' }],
            quota: 100,
          },
        ]
  );

  interface LevelType {
    name: string;
    adset: any[];
    quota: number;
  }

  const level: LevelType = { name: '', adset: [], quota: 0 };

  const handleChange = (e: any) => {
    const { name, value } = e.target;
    updateFormData({ ...data, [name]: value }, index);
  };

  const handleMultiSelectChange = (selected: string[], name: string) => {
    updateFormData({ ...data, [name]: selected }, index);
  };

  const addLevel = (): void => {
    setLevels([...levels, level]);
  };

  const deleteLevel = (index: number): void => {
    const newArr = levels.filter((d: any, i: number) => index !== i);

    setLevels(newArr);
  };

  const properties = [
    { name: 'genders', label: 'Genders' },
    { name: 'min_age', label: 'Minimum age' },
    { name: 'max_age', label: 'Maximum age' },
  ];

  return (
    <div className={classNames(index === 0 ? 'mt-4' : 'mt-8')}>
      <TextInput
        name="name"
        type="text"
        handleChange={handleChange}
        required
        autoComplete="on"
        placeholder="Give your variable a name"
        value={data.name}
      />
      <MultiSelect
        name="properties"
        options={properties}
        handleMultiSelectChange={handleMultiSelectChange}
        value={data.user_os}
        label="Select a set of properties from Facebook"
      ></MultiSelect>
      <ul>
        {levels.map((l, index) => {
          return (
            <>
              <Level
                data={l}
                index={index}
                updateFormData={updateFormData}
              ></Level>

              <>
                <div key={`${l.name}-${index}`}>
                  <div className="flex flex-row w-4/5 justify-between items-center">
                    <div className="w-4/5 h-0.5 mr-8 my-4 rounded-md bg-gray-400"></div>
                    <DeleteButton
                      onClick={() => deleteLevel(index)}
                    ></DeleteButton>
                  </div>
                  <div />
                </div>
              </>
            </>
          );
        })}
      </ul>
      <div className="flex flex-row items-center mb-4">
        <AddButton onClick={addLevel} />
        <span className="ml-4 italic text-gray-700 text-sm">Add a level</span>
      </div>
      {index !== formData.length - 1 && (
        <div className="w-4/5 h-0.5 mr-8 my-4 rounded-md bg-gray-400"></div>
      )}
    </div>
  );
};

export default Variable;
