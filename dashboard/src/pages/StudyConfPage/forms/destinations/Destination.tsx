import React, { useEffect, useState } from 'react';
import Messenger from './Messenger';
import Web from './Web';
import App from './App';
import { GenericSelect, SelectI } from '../../components/Select';
import { createLabelFor } from '../../../../helpers/strings';
import destinationTypes from '../../../../fixtures/general/destinations';
import { Destination as DestinationType } from '../../../../types/conf';

const Select = GenericSelect as SelectI<any>;

interface Props {
  data: any;
  type: string;
  index: number;
  updateFormData: (d: DestinationType, index: number) => void;
}

const Destination: React.FC<Props> = ({
  data,
  type,
  index,
  updateFormData,
}: Props) => {
  const [destinationType, setDestinationType] = useState<string>(type);

  useEffect(() => {
    setDestinationType(type);
  }, [type]);

  const initialState: any[] = [
    { name: '', initial_shortcode: '', type: 'messenger' },
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
    const fields = initialState.find((obj: any) => obj.type === value);
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
