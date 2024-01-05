import React from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { Web as FormData } from '../../../../types/conf';

const TextInput = GenericTextInput as TextInputI<FormData>;

interface Props {
  data: FormData;
  updateFormData: (e: any, index: number) => void;
  index: number;
}

const Web: React.FC<Props> = ({ data, updateFormData, index }: Props) => {
  const handleChange = (e: any) => {
    const { name, value } = e.target;
    updateFormData({ ...data, [name]: value }, index);
  };

  return (
    <>
      <TextInput
        name="name"
        handleChange={handleChange}
        placeholder="E.g web app 123"
        value={data.name}
      />
      <TextInput
        name="url_template"
        handleChange={handleChange}
        placeholder="E.g 12345"
        value={data.url_template}
      />
    </>
  );
};

export default Web;
