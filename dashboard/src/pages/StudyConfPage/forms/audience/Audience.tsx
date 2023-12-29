import React from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { Audience as FormData } from '../../../../types/conf';

const TextInput = GenericTextInput as TextInputI<FormData>;

interface Props {
  data: FormData;
  update: (e: any, index: number) => void;
  index: number;
}

const Audience: React.FC<Props> = ({ data, update, index }: Props) => {
  const handleChange = (e: any) => {
    const { name, value } = e.target;
    update({ ...data, [name]: value }, index);
  };

  return (
    <li>
      <TextInput
        name="name"
        handleChange={handleChange}
        placeholder="E.g Give your audience a name"
        value={data.name}
      />
      <TextInput
        name="subtype"
        handleChange={handleChange}
        placeholder="Add a subtype"
        value={data.subtype}
      />
    </li>
  );
};

export default Audience;
