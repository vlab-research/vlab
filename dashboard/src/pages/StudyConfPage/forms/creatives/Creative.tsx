import React, { useEffect, useState } from 'react';
import { useHistory } from 'react-router-dom';
import AddButton from '../../../../components/AddButton';
import { GenericSelect, SelectI } from '../../components/Select';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { Creative as CreativeType } from '../../../../types/conf';
import { Destinations as DestinationTypes } from '../../../../types/conf';
import { Creative as FormData } from '../../../../types/conf';

const TextInput = GenericTextInput as TextInputI<CreativeType>;
const Select = GenericSelect as SelectI<FormData>;

interface Props {
  data: FormData;
  index: number;
  destinations: DestinationTypes;
  updateFormData: (e: CreativeType, index: number) => void;
  studySlug: string;
  ads: any[];
}

const Creative: React.FC<Props> = ({
  data,
  index,
  destinations,
  updateFormData,
  studySlug,
  ads,
}: Props) => {
  const [destination, setDestination] = useState<string>(data.destination);

  useEffect(() => {
    setDestination(data.destination);
  }, [data, destination]);

  const handleChange = (e: any) => {
    const { name, value } = e.target;
    const d = { ...data, [name]: value };
    updateFormData(d, index);
  };

  const handleSelectChange = (e: any) => {
    const { value } = e.target;
    setDestination(value);
    const clone = { ...data, destination: value };
    updateFormData(clone, index);
  };

  const handleSelectTemplate = (e: any) => {
    const { value } = e.target;

    const ad = ads.find(a => a.id === value)
    const template = ad["creative"]
    updateFormData({ ...data, template }, index)
  }

  const adOptions = [
    { name: '', label: 'Please choose an option' },
    ...(ads || []).map(a => ({ name: a.id, label: a.name }))
  ]

  const chosenAd = ads.find(a => data.template.id === a.creative.id)
  const history = useHistory();

  return (
    <li>
      <TextInput
        name="name"
        handleChange={handleChange}
        placeholder="E.g Ad_campaign_2"
        value={data.name}
      />

      {destinations ? (
        <Select
          name="destination"
          options={destinations}
          handleChange={handleSelectChange}
          value={destination}
        ></Select>
      ) : (
        <>
          <label className="my-2 block text-sm font-medium text-gray-700">
            Destination
          </label>
          <AddButton
            label="Add destination"
            onClick={() => history.push(`/studies/${studySlug}/destinations`)}
          />
        </>
      )}
      <Select
        name="template"
        options={adOptions}
        handleChange={handleSelectTemplate}
        value={chosenAd?.id || ""}
      ></Select>



    </li>
  );
};

export default Creative;
