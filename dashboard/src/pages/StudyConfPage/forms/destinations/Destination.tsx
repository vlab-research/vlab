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
  // Passed through GenericList's elementProps by Destinations. Maps a destination
  // name to the Facebook page id of its creatives, for building the m.me test link.
  pageIdByName?: Record<string, string>;
  fallbackPageId?: string;
}

const Destination: React.FC<Props> = ({
  data,
  index,
  update: updateFormData,
  pageIdByName,
  fallbackPageId,
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
    { name: '', url_template: '', type: 'website' },
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

      {destinationType === 'website' && (
        <Web data={data} updateFormData={updateFormData} index={index} />
      )}
      {destinationType === 'app' && (
        <App data={data} updateFormData={updateFormData} index={index} />
      )}
      {destinationType === 'messenger' && (
        <Messenger
          data={data}
          updateFormData={updateFormData}
          index={index}
          pageId={(data.name && pageIdByName?.[data.name]) || fallbackPageId}
        />
      )}
    </li>
  );
};

export default Destination;
