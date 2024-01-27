import React from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { TypeformConfig as FormData } from '../../../../types/conf';

const TextInput = GenericTextInput as TextInputI<FormData>;

interface Props {
  data: FormData;
  updateFormData: (e: any) => void;
}

const TypeformConfig: React.FC<Props> = ({ data, updateFormData }: Props) => {
  const handleChange = (e: any) => {
    const { name, value } = e.target;
    updateFormData({ ...data, [name]: value });
  };

  return (
    <>
      <TextInput
        name="form_id"
        handleChange={handleChange}
        placeholder="Form ID from Typeform"
        value={data.form_id}
      />
    </>
  );
};

export default TypeformConfig;
