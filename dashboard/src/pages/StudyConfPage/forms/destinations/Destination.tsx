import React, { useState } from 'react';
import Messenger from './Messenger';
import Web from './Web';
import App from './App';
import WhatsApp from './WhatsApp';
import Multi from './Multi';
import { GenericSelect, SelectI } from '../../components/Select';
import destinationTypes from '../../../../fixtures/general/destinations';
import { Destination as DestinationType } from '../../../../types/conf';
import { METADATA_MODE } from './refMode';

const Select = GenericSelect as SelectI<any>;

interface Props {
  data: any;
  index: number;
  update: (d: DestinationType, index: number) => void;
  // The destinations conf as saved, so a form can say when changing the ref
  // mode would rewrite ads that already exist.
  savedDestinations?: DestinationType[];
}

const Destination: React.FC<Props> = ({
  data,
  index,
  update: updateFormData,
  savedDestinations,
}: Props) => {

  const type_ = data.type;

  // Only a saved destination has ads in flight to rewrite. Read the saved conf
  // rather than `data`, which is the edit in progress.
  const savedDestination = savedDestinations?.[index];

  const [destinationType, setDestinationType] = useState<string>(type_);

  // One of the two places a `ref_mode` default is written, the other being
  // Destinations.tsx's initialState. Both build a NEW conf, which is the whole
  // rule: a conf that arrived without the field predates it, and resolves to
  // the behaviour it already has. Nothing here ever touches such a conf,
  // because the forms spread `...data`.
  const emptyStates: any[] = [
    {
      name: '',
      initial_shortcode: '',
      welcome_message: '',
      button_text: '',
      type: 'messenger',
      ref_mode: METADATA_MODE,
    },
    { name: '', url_template: '', type: 'website', ref_mode: METADATA_MODE },
    {
      app_install_link: '',
      app_install_state: '',
      deeplink_template: '',
      facebook_app_id: '',
      user_device: [],
      user_os: [],
      name: '',
      type: 'app',
      ref_mode: METADATA_MODE,
    },
    // `type` must be exactly 'whatsapp' and 'multi': adopt discriminates its
    // destination union on these literals, and anything else resolves to the
    // wrong class or fails to parse.
    {
      name: '',
      initial_shortcode: '',
      welcome_message: '',
      whatsapp_phone_number: '',
      type: 'whatsapp',
      ref_mode: METADATA_MODE,
    },
    {
      name: '',
      initial_shortcode: '',
      welcome_message: '',
      button_text: '',
      whatsapp_phone_number: '',
      type: 'multi',
      ref_mode: METADATA_MODE,
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
        <Web data={data} updateFormData={updateFormData} index={index} savedDestination={savedDestination} />
      )}
      {destinationType === 'app' && (
        <App data={data} updateFormData={updateFormData} index={index} savedDestination={savedDestination} />
      )}
      {destinationType === 'messenger' && (
        <Messenger data={data} updateFormData={updateFormData} index={index} savedDestination={savedDestination} />
      )}
      {destinationType === 'whatsapp' && (
        <WhatsApp data={data} updateFormData={updateFormData} index={index} savedDestination={savedDestination} />
      )}
      {destinationType === 'multi' && (
        <Multi data={data} updateFormData={updateFormData} index={index} savedDestination={savedDestination} />
      )}
    </li>
  );
};

export default Destination;
