import React from 'react';
import { Path } from 'react-hook-form';
import { createLabelFor } from '../../../../helpers/strings';

export interface FormData {
  name: string;
  subtype: string;
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
      className="block w-4/5 shadow-sm sm:text-sm rounded-md"
    />
  </div>
);

interface Props {
  data: FormData;
  updateFormData: (e: any, index: number) => void;
  index: number;
}

const Audience: React.FC<Props> = ({ data, updateFormData, index }: Props) => {
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
        placeholder="E.g Give your audience a name"
        value={data.name}
      />
      <TextInput
        name="subtype"
        type="text"
        handleChange={handleChange}
        required
        autoComplete="on"
        placeholder="Add a subtype"
        value={data.subtype}
      />
    </>
  );
};

export default Audience;
