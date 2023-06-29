import React, { useState } from 'react';
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
  required?: boolean;
  value: any;
}
export const TextInput: React.FC<TextProps> = ({
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
    <input
      name={name}
      type={type}
      autoComplete={autoComplete}
      placeholder={placeholder}
      value={value}
      required={required}
      onChange={e => handleChange(e)}
      className="block w-2/5 shadow-sm sm:text-sm rounded-md"
    />
  </div>
);

interface SelectProps {
  name: Path<FormData>;
  options: SelectOption[];
  value: string;
  onChange: any;
}

interface SelectOption {
  name: string;
  id: string;
  targeting: any;
}

const Select: React.FC<SelectProps> = ({
  name,
  options,
  value,
  onChange,
}: SelectProps) => (
  <div className="sm:my-4">
    <label className="my-2 block text-sm font-medium text-gray-700">
      {createLabelFor(name)}
    </label>
    <select
      className="w-4/5 mt-1 block shadow-sm sm:text-sm rounded-md"
      value={value}
      onChange={onChange}
    >
      {options.map((option: SelectOption, i: number) => (
        <option key={i} value={option.id}>
          {option.name}
        </option>
      ))}
    </select>
  </div>
);

interface Props {
  data: any;
  index: number;
  adsets: any[];
  properties: string[];
  handleChange: (d: any, index: number) => void;
}

const Level: React.FC<Props> = ({ adsets, data, index, handleChange, properties }: Props) => {
  const onChange = (e: any) => {
    const { name, value } = e.target;
    handleChange({ [name]: value }, index)
  };

  const onAdsetChange = (e: any) => {

    // select the adset and the targeting properties of interest
    const adset = adsets.find((a) => a.id == e.target.value);
    const targeting = properties.reduce((obj, key) => ({ ...obj, [key]: adset.targeting[key] }), {});
    handleChange({ facebook_targeting: targeting, adset_id: adset.id }, index);
  };

  return (
    <li>
      <div className="m-4">
        <TextInput
          name="name"
          type="text"
          handleChange={onChange}
          autoComplete="on"
          placeholder="Give your level a name"
          value={data.name}
        />
        <Select name="adset" options={adsets} onChange={onAdsetChange} value={data.adset_id}></Select>
        <TextInput
          name="quota"
          type="number"
          handleChange={onChange}
          autoComplete="on"
          placeholder="Give your level a name"
          value={data.quota}
        />
      </div>
    </li>
  );
};

export default Level;
