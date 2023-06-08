import React, { useState } from 'react';
import { Path } from 'react-hook-form';
import { createLabelFor } from '../../../../helpers/strings';
import user_devices from '../../../../fixtures/destinations/user_devices';
import user_os from '../../../../fixtures/destinations/user_os';

export interface FormData {
  app_install_link: string;
  app_install_state: string;
  deeplink_template: string;
  facebook_app_id: string;
  user_device: string[];
  user_os: string[];
  name: string;
}

interface TextProps {
  name: Path<FormData>;
  type: string;
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

interface MultiSelectProps {
  name: Path<FormData>;
  options: SelectOption[];
  handleMultiSelectChange: (selectedValues: string[], name: string) => void;
  value: string[];
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
        {createLabelFor(name)}
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
              className="px-4 py-2 text-gray-700 hover:bg-gray-200 sm:text-sm rounded-md cursor-pointer"
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
  data: FormData;
  handleChange: (e: any) => void;
  handleMultiSelectChange: (selectedValues: string[], name: string) => void;
}

const App: React.FC<Props> = ({
  data,
  handleChange,
  handleMultiSelectChange,
}: Props) => {
  return (
    <>
      <TextInput
        name="facebook_app_id"
        type="text"
        handleChange={handleChange}
        required
        autoComplete="on"
        placeholder=""
        value={data.facebook_app_id}
      />
      <TextInput
        name="app_install_link"
        type="text"
        handleChange={handleChange}
        required
        autoComplete="on"
        placeholder=""
        value={data.app_install_link}
      />
      <TextInput
        name="deeplink_template"
        type="text"
        handleChange={handleChange}
        required
        autoComplete="on"
        placeholder=""
        value={data.deeplink_template}
      />
      <TextInput
        name="app_install_state"
        type="text"
        handleChange={handleChange}
        required
        autoComplete="on"
        placeholder=""
        value={data.app_install_state}
      />
      <MultiSelect
        name="user_device"
        options={user_devices}
        handleMultiSelectChange={handleMultiSelectChange}
        value={data.user_device}
      ></MultiSelect>
      <MultiSelect
        name="user_os"
        options={user_os}
        handleMultiSelectChange={handleMultiSelectChange}
        value={data.user_os}
      ></MultiSelect>
      <TextInput
        name="name"
        type="text"
        handleChange={handleChange}
        required
        autoComplete="on"
        placeholder="E.g Curious Learning "
        value={data.name}
      />
    </>
  );
};

export default App;
