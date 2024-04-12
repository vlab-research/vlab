import React from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { AlchemerConfig as FormData } from '../../../../types/conf';

const TextInput = GenericTextInput as TextInputI<FormData>;

interface Props {
  data: FormData;
  updateFormData: (e: any) => void;
}

const AlchemerConfig: React.FC<Props> = ({ data, updateFormData }: Props) => {
  const handleChange = (e: any) => {
    const { name, value } = e.target;
    updateFormData({ ...data, [name]: value });
  };

  return (
    <>
      <TextInput
        name="survey_id"
        handleChange={handleChange}
        placeholder="Survey ID from Alchemer"
        value={data.survey_id}
      />
      <TextInput
        name="timezone"
        handleChange={handleChange}
        placeholder="Timezone as: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"
        value={data.timezone}
      />
    </>
  );
};

export default AlchemerConfig;
