import { Path } from 'react-hook-form';
import { createLabelFor } from '../../../../helpers/strings';

export interface FormData {
  name: string;
  adset: string;
  quota: number;
}

interface TextProps {
  name: Path<FormData>;
  type?: string;
  handleChange: (e: any) => void;
  autoComplete: string;
  placeholder: string;
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

interface SelectProps {
  name: Path<FormData>;
  options: SelectOption[];
  value: string;
}

interface SelectOption {
  name: string;
  label: string;
}

const Select: React.FC<SelectProps> = ({
  name,
  options,
  value,
}: SelectProps) => (
  <div className="sm:my-4">
    <label className="my-2 block text-sm font-medium text-gray-700">
      {createLabelFor(name)}
    </label>
    <select
      className="w-4/5 mt-1 block shadow-sm sm:text-sm rounded-md"
      value={value}
    >
      {options.map((option: SelectOption, i: number) => (
        <option key={i} value={option.name}>
          {option.label}
        </option>
      ))}
    </select>
  </div>
);

interface Props {
  data: any;
  index: number;
  updateFormData: (d: any, index: number) => void;
}

const Level: React.FC<Props> = ({ data, index, updateFormData }: Props) => {
  const handleChange = (e: any) => {
    const { name, value } = e.target;
    updateFormData({ ...data, [name]: value }, index);
  };

  const adsets = [
    { name: 'adset_1', label: 'Ad set 1' },
    { name: 'adset_2', label: 'Ad set 2' },
    { name: 'adset_3', label: 'Ad set 3' },
  ];

  return (
    <>
      <TextInput
        name="name"
        type="text"
        handleChange={handleChange}
        autoComplete="on"
        placeholder="Give your level a name"
        value={data.name}
      />
      <Select name="adset" options={adsets} value={data.adset}></Select>
      <TextInput
        name="quota"
        type="number"
        handleChange={handleChange}
        autoComplete="on"
        placeholder="Give your level a name"
        value={data.quota}
      />
    </>
  );
};

export default Level;
