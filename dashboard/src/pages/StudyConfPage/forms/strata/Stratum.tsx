import React from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { Stratum as StratumType } from '../../../../types/conf';

export interface FormData {
  id: string;
  quota: number;
}
const TextInput = GenericTextInput as TextInputI<FormData>;

const Stratum: React.FC<{
  stratum: StratumType;
  onChange: (e: any) => void;
}> = ({ stratum, onChange }) => {
  return (
    <li>
      <TextInput
        name="id"
        type="text"
        value={stratum.id}
        disabled={true}
        placeholder="name"
        handleChange={onChange}
      />
      <TextInput
        name="quota"
        type="text"
        value={stratum.quota}
        placeholder="Give your stratum a quota e.g 5"
        handleChange={onChange}
      />
    </li>
  );
};

export default Stratum;
