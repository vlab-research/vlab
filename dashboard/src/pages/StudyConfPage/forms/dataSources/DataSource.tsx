import React from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { DataSource as FormData } from '../../../../types/conf';
import { GenericSelect, SelectI } from '../../components/Select';
import { type Account } from '../../../../types/account';

const TextInput = GenericTextInput as TextInputI<FormData>;
const Select = GenericSelect as SelectI<FormData>;

interface Props {
  data: FormData;
  accounts: Account[];
  update: (e: any, index: number) => void;
  index: number;
}

const DataSource: React.FC<Props> = ({ data, update: updateFormData, index, accounts }: Props) => {
  const handleChange = (e: any) => {
    const { name, value } = e.target;
    updateFormData({ ...data, [name]: value }, index);
  };

  const sourceOptions = [
    { name: '', label: 'Please choose a data source' },
    { name: 'fly', label: 'Fly' },
    { name: 'qualtrics', label: 'Qualtrics' },
    { name: 'typeform', label: 'Typeform' },
  ]

  const validAccounts = accounts.filter(a => a.authType === data.source);

  const hasValidAccount = validAccounts.length > 0;

  const emptyMessage = hasValidAccount ?
    `Please choose ${data.source} credentials` :
    `You must first connect a ${data.source} account`

  const credentialsOptions = [
    { name: '', label: emptyMessage },
    ...validAccounts.map(a => ({ name: a.name, label: a.name }))]

  return (
    <li>
      <TextInput
        name="name"
        handleChange={handleChange}
        placeholder="A name you give this data source to refer to it by."
        value={data.name}
      />
      <Select
        name="source"
        handleChange={handleChange}
        options={sourceOptions}
        value={data.source}
      />
      <Select
        name="credentials_key"
        handleChange={handleChange}
        options={credentialsOptions}
        value={data.credentials_key}
        disabled={!hasValidAccount}
      />

    </li>
  );
};

export default DataSource;
