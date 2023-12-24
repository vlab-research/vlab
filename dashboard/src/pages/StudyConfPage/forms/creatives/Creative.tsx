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
}

const Creative: React.FC<Props> = ({
  data,
  index,
  destinations,
  updateFormData,
  studySlug,
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

  const history = useHistory();

  // TODO: add template logic

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

    </li>
  );
};

export default Creative;
