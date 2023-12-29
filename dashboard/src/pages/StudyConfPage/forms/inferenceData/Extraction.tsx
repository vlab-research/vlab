import React from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { GenericSelect, SelectI } from '../../components/Select';
import { Extraction as FormData, ExtractionFunction as ExtractionFunctionType } from '../../../../types/conf';
const TextInput = GenericTextInput as TextInputI<FormData>;
const Select = GenericSelect as SelectI<FormData>;

interface Props {
  data: FormData;
  update: (e: any, index: number) => void;
  index: number;
  sourceType: string;
}

const Extraction: React.FC<Props> = ({ data, update, index, sourceType }: Props) => {

  return (
    <li>

    </li>
  );
};

export default Extraction;
