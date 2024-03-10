import React, { useState } from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { Messenger as FormData } from '../../../../types/conf';

const TextInput = GenericTextInput as TextInputI<FormData>;

interface Props {
  data: FormData;
  updateFormData: (e: any, index: number) => void;
  index: number;
}

const Messenger: React.FC<Props> = ({ data, updateFormData, index }: Props) => {
  const handleChange = (e: any) => {
    const { name, value } = e.target;
    updateFormData({ ...data, [name]: value }, index);
  };

  const handleMetadata = (e: any) => {
    const { name, value } = e.target;

    if (!value) {
      setMetadata(value)
      updateFormData({ ...data, [name]: null }, index)
      return
    }

    let md;

    try {
      md = JSON.parse(value)
    } catch (e) {
      setMetadata(value)
      return
    }

    setMetadata(value)
    updateFormData({ ...data, [name]: md }, index)
  }

  const additional_metadata = data.additional_metadata ? JSON.stringify(data.additional_metadata) : "";

  const [metadata, setMetadata] = useState<string>(additional_metadata);

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
