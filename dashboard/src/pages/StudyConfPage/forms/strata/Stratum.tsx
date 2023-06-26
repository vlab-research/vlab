import { Path } from 'react-hook-form';
import { createLabelFor } from '../../../../helpers/strings';

export interface FormData {
  name: string;
  level: string;
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

interface Props {
  data: any;
  index: number;
  updateFormData: (d: any, index: number) => void;
}

const Stratum: React.FC<Props> = ({ data, index, updateFormData }: Props) => {
  const initialState: any[] = [{ name: '', level: '' }];

  const handleChange = (e: any) => {
    const { name, value } = e.target;
    updateFormData({ ...data, [name]: value }, index);
  };

  return (
    <>
      <TextInput
        name="name"
        type="text"
        handleChange={handleChange}
        required
        autoComplete="on"
        placeholder="Give your variable a name"
        value={data.name}
      />
      <TextInput
        name="level"
        type="text"
        handleChange={handleChange}
        required
        autoComplete="on"
        placeholder="Add a level for you variable e.g. M"
        value={data.level}
      />
    </>
  );
};

export default Stratum;
