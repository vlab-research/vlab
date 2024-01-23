import React from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { FlyConfig as FormData } from '../../../../types/conf';

const TextInput = GenericTextInput as TextInputI<FormData>;

interface Props {
  data: FormData;
  updateFormData: (FormData: any) => void;
}

const FlyConfig: React.FC<Props> = ({ data, updateFormData }: Props) => {
  const handleChange = (e: any) => {
    const { name, value } = e.target;
    updateFormData({ ...data, [name]: value });
  };

  return (
    <>
      <TextInput
        name="survey_name"
        handleChange={handleChange}
        placeholder="The Survey Name In Fly"
        value={data.survey_name}
      />
    </>
  );
};

export default FlyConfig;
