import React from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { Audience as AudienceType } from '../../../../types/conf';

export const TextInput = GenericTextInput as TextInputI<AudienceType>;

interface Props {
  data: AudienceType;
  updateFormData: (e: any, index: number) => void;
  index: number;
}
const Audience: React.FC<Props> = ({ data, updateFormData, index }: Props) => {
  const handleChange = (e: any) => {
    const { name, value } = e.target;
    updateFormData({ ...data, [name]: value }, index);
  };

  return (
    <>
      <TextInput
        name="name"
        type="text"
        handleChange={handleChange}
        required
        autoComplete="on"
        placeholder="E.g Give your audience a name"
        value={data.name}
      />
      <TextInput
        name="subtype"
        type="text"
        handleChange={handleChange}
        required
        autoComplete="on"
        placeholder="Add a subtype"
        value={data.subtype}
      />
    </>
  );
};

export default Audience;
