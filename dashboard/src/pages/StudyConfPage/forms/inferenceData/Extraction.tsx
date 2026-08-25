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
  responseOptions,
  responsePrompt,
} from './extraction';


interface ExtractionForm extends FormData {
  response: string;
}
const TextInput = GenericTextInput as TextInputI<ExtractionForm>;
const Select = GenericSelect as SelectI<ExtractionForm>;


interface Props {
  data: FormData;
  update: (e: any, index: number) => void;
  index: number;
  nameOptions: string[];
  source: string;
}

// One control for every source. Location says where to read and mapping says
// what the value means, and neither depends on the connector, so a Typeform
// source declares an ad lookup exactly as a fly source does — it just names the
// field its token comes back in rather than a metadata key.
const Extraction: React.FC<Props> = ({ data, nameOptions: names, update: updateFormData, index, source }: Props) => {

  const handleChange = (e: any) => {
    const { name, value } = e.target;
    updateFormData(applyChange(data, name, value), index);
  };

  // `metadata` is a keyed read under either mapping, so it has no response
  // path to select. Expressed as one concept rather than scattered checks.
  const isKeyed = isKeyedLocation(data.location);
  const response = data?.functions[0]?.params.path || "";

  const responses = [
    { name: '', label: responsePrompt(data.location) },
    ...responseOptions(source),
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
      <Select
        name="mapping"
        handleChange={handleChange}
        options={mappingOptions}
        value={data.mapping || 'raw'}
      />
      <TextInput
        name="key"
        handleChange={handleChange}
        placeholder={keyPlaceholder(data)}
        value={data.key}
      />
      <Select
        name="response"
        handleChange={handleChange}
        options={responses}
        value={response}
        disabled={isKeyed}
        required={!isKeyed}
      />
    </li>
  );
};

export default Extraction;
