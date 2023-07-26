import React from 'react';
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

  return (
    <>
      <TextInput
        name="initial_shortcode"
        handleChange={handleChange}
        placeholder="E.g 12345"
        value={data.initial_shortcode}
      />
      <TextInput
        name="name"
        handleChange={handleChange}
        placeholder="E.g fly"
        value={data.name}
      />
    </>
  );
};

export default Messenger;
