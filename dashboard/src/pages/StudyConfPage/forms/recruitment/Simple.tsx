import React from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { RecruitmentSimple as FormData } from '../../../../types/conf';

const TextInput = GenericTextInput as TextInputI<FormData>;

interface Props {
  formData: FormData;
  updateFormData: (e: any) => void;
}

const validateInput = (name: string, value: any) => {
  if (name === 'budget' || name === 'max_sample') {
    if (!value) {
      return parseInt('0');
    }
    return parseInt(value);
  } else return value;
};

const Simple: React.FC<Props> = ({ formData, updateFormData }: Props) => {
  const handleChange = (e: any) => {
    const { name, value } = e.target;
    updateFormData({ ...formData, [name]: validateInput(name, value) });
  };

  return (
    <>
      <TextInput
        name="ad_campaign_name"
        handleChange={handleChange}
        placeholder="E.g vlab-vaping-pilot-2"
        value={formData.ad_campaign_name}
      />
      <TextInput
        name="budget"
        handleChange={handleChange}
        placeholder="E.g 8400"
        value={formData.budget}
      />
      <TextInput
        name="max_sample"
        handleChange={handleChange}
        placeholder="E.g 1000"
        value={formData.max_sample}
      />
      <TextInput
        name="start_date"
        handleChange={handleChange}
        placeholder="E.g 2022-07-26T00:00:00"
        value={formData.start_date}
      />
      <TextInput
        name="end_date"
        handleChange={handleChange}
        placeholder="E.g 2022-07-26T00:00:00"
        value={formData.end_date}
      />
    </>
  );
};

export default Simple;
