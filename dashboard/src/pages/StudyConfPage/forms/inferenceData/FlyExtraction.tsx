import React from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { GenericSelect, SelectI } from '../../components/Select';
import { Extraction as FormData } from '../../../../types/conf'
import {
  applyChange,
  isKeyedLocation,
  keyPlaceholder,
  locationOptions,
  mappingOptions,
  namePrompt,
  responsePrompt,
  showsMapping,
} from './flyExtraction';


interface FlyExtractionForm extends FormData {
  response: string;
}
const TextInput = GenericTextInput as TextInputI<FlyExtractionForm>;
const Select = GenericSelect as SelectI<FlyExtractionForm>;


interface Props {
  data: FormData;
  update: (e: any, index: number) => void;
  index: number;
  nameOptions: string[];
}

const FlyExtraction: React.FC<Props> = ({ data, nameOptions: names, update: updateFormData, index }: Props) => {


  const handleChange = (e: any) => {
    const { name, value } = e.target;
    updateFormData(applyChange(data, name, value), index);
  };

  // `metadata` is a keyed lookup under either mapping, so it has no response
  // path to select. Expressed as one concept rather than scattered checks.
  const isKeyed = isKeyedLocation(data.location);
  const response = data?.functions[0]?.params.path || "";

  const responseOptions = [
    { name: '', label: responsePrompt(data.location) },
    { name: 'response', label: 'Response' },
    { name: 'translated_response', label: 'Translated Response' },
  ]

  const nameOptions = [
    { name: '', label: namePrompt(data) },
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
      {showsMapping(data.location) && (
        <Select
          name="mapping"
          handleChange={handleChange}
          options={mappingOptions}
          value={data.mapping || 'raw'}
        />
      )}
      <TextInput
        name="key"
        handleChange={handleChange}
        placeholder={keyPlaceholder(data)}
        value={data.key}
      />
      <Select
        name="response"
        handleChange={handleChange}
        options={responseOptions}
        value={response}
        disabled={isKeyed}
        required={!isKeyed}
      />
    </li>
  );
};

export default FlyExtraction;
