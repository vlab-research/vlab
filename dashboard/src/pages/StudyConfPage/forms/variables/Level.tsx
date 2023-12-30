import React from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { GenericSelect, SelectI } from '../../components/Select';

export interface FormData {
  name: string;
  adset: string;
  quota: number;
}

const TextInput = GenericTextInput as TextInputI<FormData>;
const Select = GenericSelect as SelectI<FormData>;

interface Props {
  data: any;
  index: number;
  adsets: any[];
  properties: string[];
  update: (d: any, index: number) => void;
}

const Level: React.FC<Props> = ({
  adsets,
  data,
  index,
  update: handleChange,
  properties,
}: Props) => {

  const onChange = (e: any) => {
    const { name, value } = e.target;
    handleChange({ ...data, [name]: value }, index);
  };

  const onAdsetChange = (e: any) => {
    // selects the adset and the targeting properties of interest
    const adset = adsets.find(a => a.id === e.target.value);

    if (!adset) {
      throw new Error(`adset not found. Looking for ${e.target.value}. Adset: ${adsets}`)
    }
    const targeting = properties.reduce(
      (obj, key) => ({ ...obj, [key]: adset.targeting[key] }),
      {}
    );
    handleChange(
      { facebook_targeting: targeting, template_adset: adset.id },
      index
    );
  };

  return (
    <li>
      <div className="m-4">
        <TextInput
          name="name"
          handleChange={onChange}
          autoComplete="on"
          placeholder="Give your level a name"
          value={data.name}
        />
        <Select
          name="adset"
          options={adsets}
          handleChange={onAdsetChange}
          value={data.template_adset}
          getValue={(o: any) => o.id}
        ></Select>
        <TextInput
          name="quota"
          handleChange={onChange}
          placeholder="Give your a quota"
          value={data.quota}
        />
      </div>
    </li>
  );
};

export default Level;
