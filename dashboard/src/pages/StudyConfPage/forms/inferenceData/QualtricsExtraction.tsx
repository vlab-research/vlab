import React from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { GenericSelect, SelectI } from '../../components/Select';
import { Extraction as FormData } from '../../../../types/conf';


interface QualtricsExtractionForm extends FormData {
  response: string;
}
const TextInput = GenericTextInput as TextInputI<QualtricsExtractionForm>;
const Select = GenericSelect as SelectI<QualtricsExtractionForm>;


interface Props {
  data: FormData;
  update: (e: any, index: number) => void;
  index: number;
  nameOptions: string[];
}

const QualtricsExtraction: React.FC<Props> = ({ data, nameOptions: names, update: updateFormData, index }: Props) => {

  const handleChange = (e: any) => {
    const { name, value } = e.target;

    const update = { [name]: value }

    updateFormData({
      ...data,
      value_type: "categorical",
      aggregate: "first",
      functions: [{ function: "select", params: { path: '' } }],
      ...update
    }, index);
  };

  const locationOptions = [
    { name: '', label: 'Where is the data located in the source?' },
    { name: 'metadata', label: 'Metadata' },
    { name: 'variable', label: 'Variable' },
  ]

  const nameOptions = [
    { name: '', label: 'What name do you use to refer to this variable?' },
    names.map(n => ({ name: n, label: n }))
  ]

  return (
    <li>
      <Select
        name="name"
        handleChange={handleChange}
        options={nameOptions}
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
        value={data.key}
      />
    </li>
  );
};

export default QualtricsExtraction;
