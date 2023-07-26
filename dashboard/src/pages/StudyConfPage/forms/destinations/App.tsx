import React, { useState } from 'react';
import { Path } from 'react-hook-form';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { createLabelFor } from '../../../../helpers/strings';
import user_devices from '../../../../fixtures/destinations/user_devices';
import user_os from '../../../../fixtures/destinations/user_os';
import { App as FormData } from '../../../../types/conf';

const TextInput = GenericTextInput as TextInputI<FormData>;

interface MultiSelectProps {
  name: Path<FormData>;
  options: { name: string; label: string }[];
  handleMultiSelectChange: (selectedValues: string[], name: string) => void;
  value: string[];
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
        {options.map((option: { name: string; label: string }, i: number) => (
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
  updateFormData: (e: any, index: number) => void;
  index: number;
}

const App: React.FC<Props> = ({ data, updateFormData, index }: Props) => {
  const handleChange = (e: any) => {
    const { name, value } = e.target;
    updateFormData({ ...data, [name]: value }, index);
  };

  const handleMultiSelectChange = (selected: string[], name: string) => {
    updateFormData({ ...data, [name]: selected }, index);
  };

  return (
    <>
      <TextInput
        name="facebook_app_id"
        handleChange={handleChange}
        placeholder=""
        value={data.facebook_app_id}
      />
      <TextInput
        name="app_install_link"
        handleChange={handleChange}
        placeholder=""
        value={data.app_install_link}
      />
      <TextInput
        name="deeplink_template"
        handleChange={handleChange}
        placeholder=""
        value={data.deeplink_template}
      />
      <TextInput
        name="app_install_state"
        handleChange={handleChange}
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
        handleChange={handleChange}
        placeholder="E.g Curious Learning "
        value={data.name}
      />
    </>
  );
};

export default App;
