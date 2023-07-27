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

  return (
    <li>
      <TextInput
        name="name"
        handleChange={handleChange}
        placeholder="E.g Ad_campaign_2"
        value={data.name}
      />

      <TextInput
        name="image_hash"
        type="text"
        handleChange={handleChange}
        autoComplete="on"
        placeholder="E.g 8ef11493ade6deced04f36b9e8cf3900"
        value={data.image_hash}
      />
      <TextInput
        name="body"
        handleChange={handleChange}
        autoComplete="on"
        placeholder="This is the text of the post that will be the ad."
        value={data.body}
      />
      <TextInput
        name="link_text"
        type="text"
        handleChange={handleChange}
        autoComplete="on"
        placeholder="This is the 'headline' text next to the CTA button."
        value={data.link_text}
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
      <TextInput
        name="welcome_message"
        handleChange={handleChange}
        autoComplete="on"
        placeholder="This is a message the user will see in the chat."
        value={data.welcome_message}
        required={false}
      />
      <TextInput
        name="button_text"
        type="text"
        handleChange={handleChange}
        autoComplete="on"
        placeholder="This is the button the user will see in the chat."
        value={data.button_text}
        required={false}
      />
    </li>
  );
};

export default Creative;
