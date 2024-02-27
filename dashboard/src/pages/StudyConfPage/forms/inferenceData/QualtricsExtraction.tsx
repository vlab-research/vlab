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

  const getFunctions = (x: string) => {
    return [{ function: "select", params: { path: x } }]
  }

  const handleChange = (e: any) => {
    const { name, value } = e.target;

    let update;

    switch (name) {
      case "response":
        update = { functions: getFunctions(value) }
        break

      case "location":
        update = {
          location: value,
          functions: value === "metadata" ? [{ function: "select", params: { path: "" } }] : data.functions
        }
        break

      default:
        update = { [name]: value }
    }

    updateFormData({
      ...data,
      value_type: "categorical",
      aggregate: "first",
      ...update
    }, index);
  };

  const locationOptions = [
    { name: '', label: 'Where is the data located in the source?' },
    { name: 'metadata', label: 'Metadata' },
    { name: 'variable', label: 'Variable' },
  ]

  const isMetadata = data.location === "metadata";
  const response = data?.functions[0]?.params.path || "response";

  const responseOptions = [
    { name: '', label: isMetadata ? "Select from Metadata" : 'Which response value do you want to use?' },
    { name: 'label', label: 'Label' },
    { name: 'value', label: 'Value' },
  ]

  const nameOptions = [
    { name: '', label: 'What name do you use to refer to this variable?' },
    ...names.map(n => ({ name: n, label: n }))
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
      <Select
        name="response"
        handleChange={handleChange}
        options={responseOptions}
        value={response}
        disabled={isMetadata}
        required={!isMetadata}
      />
    </li>
  );
};

export default QualtricsExtraction;
