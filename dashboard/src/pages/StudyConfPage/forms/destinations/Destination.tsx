import React, { useState } from 'react';
import Messenger from './Messenger';
import Web from './Web';
import App from './App';
import { GenericSelect, SelectI } from '../../components/Select';
import destinationTypes from '../../../../fixtures/general/destinations';
import { Destination as DestinationType } from '../../../../types/conf';

const Select = GenericSelect as SelectI<any>;

interface Props {
  data: any;
  index: number;
  update: (d: DestinationType, index: number) => void;
}

const Destination: React.FC<Props> = ({
  data,
  index,
  update: updateFormData,
}: Props) => {

  const type_ = data.type;

  const [destinationType, setDestinationType] = useState<string>(type_);

  const emptyStates: any[] = [
    {
      name: '',
      initial_shortcode: '',
      welcome_message: '',
      button_text: '',
      type: 'messenger'
    },
    { name: '', url_template: '', type: 'web' },
    {
      app_install_link: '',
      app_install_state: '',
      deeplink_template: '',
      facebook_app_id: '',
      user_device: [],
      user_os: [],
      name: '',
      type: 'app',
    },
  ];

  const handleSelectChange = (e: any) => {
    const { value } = e.target;
    setDestinationType(value);
    const fields = emptyStates.find((obj: any) => obj.type === value);
    if (!fields) return;
    updateFormData(fields, index);
  };

  return (
    <li>
      <Select
        name="destination_type"
        options={destinationTypes}
        handleChange={handleSelectChange}
        value={destinationType}
        label="Select a destination type"
      ></Select>

      {destinationType === 'web' && (
        <Web data={data} updateFormData={updateFormData} index={index} />
      )}
      {destinationType === 'app' && (
        <App data={data} updateFormData={updateFormData} index={index} />
      )}
      {destinationType === 'messenger' && (
        <Messenger data={data} updateFormData={updateFormData} index={index} />
      )}
    </li>
  );
};

export default Destination;
