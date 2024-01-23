import React from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { QualtricsConfig as FormData } from '../../../../types/conf';

const TextInput = GenericTextInput as TextInputI<FormData>;

interface Props {
  data: FormData;
  updateFormData: (e: any) => void;
}

const QualtricsConfig: React.FC<Props> = ({ data, updateFormData }: Props) => {
  const handleChange = (e: any) => {
    const { name, value } = e.target;
    updateFormData({ ...data, [name]: value });
  };

  return (
    <>
      <TextInput
        name="survey_id"
        handleChange={handleChange}
        placeholder="Survey ID from Qualtrics"
        value={data.survey_id}
      />
    </>
  );
};

export default QualtricsConfig;
