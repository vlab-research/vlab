import React from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { GenericSelect, SelectI } from '../../components/Select';
import { Extraction as FormData, ExtractionFunction as ExtractionFunctionType } from '../../../../types/conf';
const TextInput = GenericTextInput as TextInputI<FormData>;
const Select = GenericSelect as SelectI<FormData>;

interface Props {
  data: FormData;
  updateFormData: (e: any, index: number) => void;
  index: number;
}

const DataSource: React.FC<Props> = ({ data, updateFormData, index }: Props) => {
  const handleChange = (e: any) => {
    const { name, value } = e.target;
    updateFormData({ ...data, [name]: value }, index);
  };

  const locationOptions = [
    { name: '', label: 'Where is the data located in the source?' },
    { name: 'metadata', label: 'Metadata' },
    { name: 'variable', label: 'Variable' },
  ]

  const aggregateOptions = [
    { name: '', label: 'How do we aggregate multiple values' },
    { name: 'first', label: 'First' },
    { name: 'last', label: 'Last' },
    { name: 'max', label: 'Max' },
    { name: 'min', label: 'Min' },
  ]

  const valueTypeOptions = [
    { name: '', label: 'What type of value is this? ' },
    { name: 'categorical', label: 'Categorical' },
    { name: 'continuous', label: 'Continuous' },
  ]

  // What to do about extraction functions?
  // You could force this to be different based on the source.
  // Some sources can support some ways of doing this.
  // This will allow you to make this much more user friendly...
  // While the flexibility exists in the back...

  return (
    <li>
      <TextInput
        name="name"
        handleChange={handleChange}
        placeholder="What name do you want to give this variable?"
        value={data.name}
      />
      <Select
        name="location"
        handleChange={handleChange}
        options={locationOptions}
        value={data.location}
      />
      <TextInput
        name="key"
        handleChange={handleChange}
        placeholder="What is the variable called in the data source?"
        value={data.name}
      />
      <Select
        name="value_type"
        handleChange={handleChange}
        options={valueTypeOptions}
        value={data.value_type}
      />
      <Select
        name="aggregate"
        handleChange={handleChange}
        options={aggregateOptions}
        value={data.aggregate}
      />
    </li>
  );
};

export default DataSource;
