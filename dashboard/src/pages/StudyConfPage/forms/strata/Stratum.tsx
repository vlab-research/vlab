import React from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { GenericMultiSelect, MultiSelectI } from '../../components/MultiSelect';
import { Stratum as FormData, Creative as CreativeType } from '../../../../types/conf';

const TextInput = GenericTextInput as TextInputI<FormData>;
const MultiSelect = GenericMultiSelect as MultiSelectI<FormData>;

const Stratum: React.FC<{
  stratum: FormData;
  creatives: CreativeType[];
  onChange: (e: any) => void;
}> = ({ stratum, onChange, creatives }) => {

  const handleMultiSelectChange = (selected: string[], name: string) => {
    onChange({ target: { name, value: selected } });
  };

  return (
    <li>
      <TextInput
        name="id"
        value={stratum.id}
        disabled={true}
        placeholder="name"
        handleChange={onChange}
      />
      <TextInput
        name="quota"
        value={stratum.quota}
        placeholder="Give your stratum a quota e.g 5"
        handleChange={onChange}
      />
      <MultiSelect
        name="creatives"
        options={creatives.map(c => ({ label: c.name, value: c.name }))}
        handleMultiSelectChange={handleMultiSelectChange}
        value={stratum.creatives}
        label="Select a set of creatives for this stratum"
      ></MultiSelect>
      <div className="w-4/5 h-0.5 mr-8 my-6 rounded-md bg-gray-400"></div>
    </li>
  );
};

export default Stratum;
