import React from 'react';
import { Path } from 'react-hook-form';
import { createLabelFor } from '../../../../helpers/strings';

export interface FormData {
  name: string;
  initial_shortcode: string;
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
  handleChange: (e: any) => void;
}

const Messenger: React.FC<Props> = ({ data, handleChange }: Props) => {
  return (
    <>
      <TextInput
        name="initial_shortcode"
        type="text"
        handleChange={handleChange}
        required
        autoComplete="on"
        placeholder="E.g 12345"
        value={data.initial_shortcode}
      />
      <TextInput
        name="name"
        type="text"
        handleChange={handleChange}
        required
        autoComplete="on"
        placeholder="E.g fly"
        value={data.name}
      />
    </>
  );
};

export default Messenger;
