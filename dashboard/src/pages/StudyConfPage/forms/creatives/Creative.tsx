import React, { useEffect, useState } from 'react';
import { Destinations as DestinationTypes } from '../../../../types/conf';
import { Path } from 'react-hook-form';
import { createLabelFor } from '../../../../helpers/strings';
import { Creative as CreativeType } from '../../../../types/conf';

interface FormData {
  name: string;
  body: string;
  button_text?: string | undefined;
  destination: string;
  image_hash: string;
  link_text: string;
  welcome_message?: string | undefined;
  tags: null;
}

interface TextProps {
  name: Path<FormData>;
  type?: string;
  handleChange: (e: any) => void;
  autoComplete: string;
  placeholder: string;
  value: any;
  required?: boolean;
}
const TextInput: React.FC<TextProps> = ({
  name,
  type,
  handleChange,
  autoComplete,
  placeholder,
  value,
  required = true,
}) => (
  <div className="sm:my-4">
    <label className="my-2 block text-sm font-medium text-gray-700">
      {createLabelFor(name)}
    </label>
    <div className="flex flex-row items-center">
      <input
        name={name}
        type={type}
        autoComplete={autoComplete}
        placeholder={placeholder}
        value={value}
        required={required}
        onChange={e => handleChange(e)}
        className="block w-4/5 shadow-sm sm:text-sm rounded-md"
      />
      {required === false && (
        <span className="ml-4 italic text-gray-700 text-xs">Optional</span>
      )}
    </div>
  </div>
);

interface SelectProps {
  name: Path<FormData>;
  value: string;
  options: DestinationTypes;
  handleSelectChange: (e: any) => void;
}

interface SelectOption {
  name: string;
}

const Select: React.FC<SelectProps> = ({
  name,
  value,
  options,
  handleSelectChange,
}: SelectProps) => (
  <div className="sm:my-4">
    <label className="my-2 block text-sm font-medium text-gray-700">
      {createLabelFor(name)}
    </label>
    <select
      required
      value={value}
      onChange={handleSelectChange}
      className="w-4/5 block shadow-sm sm:text-sm rounded-md"
    >
      {options.map((option: SelectOption, i: number) => (
        <option key={i} value={option.name}>
          {option.name}
        </option>
      ))}
    </select>
  </div>
);

interface Props {
  data: FormData;
  index: number;
  destinations: DestinationTypes;
  updateFormData: (e: CreativeType, index: number) => void;
}

const Creative: React.FC<Props> = ({
  data,
  index,
  destinations,
  updateFormData,
}: Props) => {
  const handleChange = (e: any) => {
    const { name, value } = e.target;
    const d = { ...data, [name]: value };
    updateFormData(d, index);
  };

  const [destination, setDestination] = useState<string>(data.destination);

  useEffect(() => {
    setDestination(data.destination);
  }, [data, destination]);

  const handleSelectChange = (e: any) => {
    const { value } = e.target;
    setDestination(value);
    const clone = { ...data, destination: value };
    updateFormData(clone, index);
  };

  return (
    <li>
      <TextInput
        name="name"
        type="text"
        handleChange={handleChange}
        autoComplete="on"
        placeholder="E.g Ad_campaign_2"
        value={data.name}
      />

      <TextInput
        name="image_hash"
        type="text"
        handleChange={handleChange}
        autoComplete="on"
        placeholder="E.g 8ef11493ade6deced04f36b9e8cf3900"
        value={data.image_hash}
      />
      <TextInput
        name="body"
        type="text"
        handleChange={handleChange}
        autoComplete="on"
        placeholder="This is the text of the post that will be the ad."
        value={data.body}
      />
      <TextInput
        name="link_text"
        type="text"
        handleChange={handleChange}
        autoComplete="on"
        placeholder="This is the 'headline' text next to the CTA button."
        value={data.link_text}
      />

      {destinations ? (
        <Select
          name="destination"
          options={destinations}
          value={data.destination}
          handleSelectChange={handleSelectChange}
        ></Select>
      ) : (
        <>
          <label className="my-2 block text-sm font-medium text-gray-700">
            Destination
          </label>
          <div className="p-2 block w-4/5 sm:text-sm">
            <span className="sm:text-sm text-gray-700">
              Add a destination...
            </span>
          </div>
        </>
      )}

      <TextInput
        name="welcome_message"
        type="text"
        handleChange={handleChange}
        autoComplete="on"
        placeholder="This is a message the user will see in the chat."
        value={data.welcome_message}
        required={false}
      />
      <TextInput
        name="button_text"
        type="text"
        handleChange={handleChange}
        autoComplete="on"
        placeholder="This is the button the user will see in the chat."
        value={data.button_text}
        required={false}
      />
    </li>
  );
};

export default Creative;
