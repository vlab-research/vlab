import React, { useState } from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { Messenger as FormData, Destination } from '../../../../types/conf';
import { metadataToText, parseAdditionalMetadata } from './additionalMetadata';
import RefModeField from './RefModeField';

const TextInput = GenericTextInput as TextInputI<FormData>;

interface Props {
  data: FormData;
  updateFormData: (e: any, index: number) => void;
  index: number;
  destinations: Destination[];
}

const Messenger: React.FC<Props> = ({
  data,
  updateFormData,
  index,
  destinations,
}: Props) => {
  const handleChange = (e: any) => {
    const { name, value } = e.target;
    updateFormData({ ...data, [name]: value }, index);
  };

  const handleMetadata = (e: any) => {
    const { name, value } = e.target;
    setMetadata(value);

    const result = parseAdditionalMetadata(value);
    if (result.kind === 'invalid') return;

    updateFormData(
      { ...data, [name]: result.kind === 'empty' ? null : result.value },
      index
    );
  };

  const [metadata, setMetadata] = useState<string>(
    metadataToText(data.additional_metadata)
  );

  return (
    <>
      <TextInput
        name="name"
        handleChange={handleChange}
        placeholder="E.g fly messenger"
        value={data.name}
      />
      <TextInput
        name="initial_shortcode"
        handleChange={handleChange}
        placeholder="E.g 12345"
        value={data.initial_shortcode}
      />
      <TextInput
        name="welcome_message"
        handleChange={handleChange}
        placeholder="E.g Welcome to our survey. Would you like to continue?"
        value={data.welcome_message}
      />
      <TextInput
        name="button_text"
        handleChange={handleChange}
        placeholder="E.g OK"
        value={data.button_text}
      />
      <RefModeField refMode={data.ref_mode} handleChange={handleChange} />
      <TextInput
        name="additional_metadata"
        handleChange={handleMetadata}
        placeholder={`String key-value pairs e.g. {"foo": "bar"}`}
        required={false}
        value={metadata}
      />
    </>
  );
};

export default Messenger;
