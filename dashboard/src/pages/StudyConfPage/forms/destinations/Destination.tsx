import React, { useState } from 'react';
import Messenger from './Messenger';
import Web from './Web';
import App from './App';
import WhatsApp from './WhatsApp';
import Multi from './Multi';
import { GenericSelect, SelectI } from '../../components/Select';
import destinationTypes from '../../../../fixtures/general/destinations';
import { Destination as DestinationType } from '../../../../types/conf';
import { initialRefMode } from './refMode';

const Select = GenericSelect as SelectI<any>;

interface Props {
  data: any;
  index: number;
  update: (d: DestinationType, index: number) => void;
  /**
   * Every destination in the study. Needed because "may this destination use
   * the inline-stratum link?" is a whole-study question, not a per-destination
   * one — see refMode.isPureMessengerStudy.
   */
  destinations: DestinationType[];
}

const Destination: React.FC<Props> = ({
  data,
  index,
  update: updateFormData,
  destinations,
}: Props) => {

  const type_ = data.type;

  const [destinationType, setDestinationType] = useState<string>(type_);

  const emptyStates: any[] = [
    // ref_mode is set here, on creation, and nowhere that runs on load. That
    // split is what lets the model keep defaulting to legacy (absent resolves
    // per channel, so no stored conf is reinterpreted) while new confs are
    // explicitly encoded. See refMode.ts and planning/ref-mode-dashboard-ux.md.
    {
      name: '',
      initial_shortcode: '',
      welcome_message: '',
      button_text: '',
      ref_mode: initialRefMode(),
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
    // `type` must be exactly 'whatsapp' and 'multi': adopt discriminates its
    // destination union on these literals, and anything else resolves to the
    // wrong class or fails to parse.
    {
      name: '',
      initial_shortcode: '',
      welcome_message: '',
      whatsapp_phone_number: '',
      ref_mode: initialRefMode(),
      type: 'whatsapp',
    },
    {
      name: '',
      initial_shortcode: '',
      welcome_message: '',
      button_text: '',
      whatsapp_phone_number: '',
      ref_mode: initialRefMode(),
      type: 'multi',
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
          destinations={destinations}
        />
      )}
      {destinationType === 'whatsapp' && (
        <WhatsApp
          data={data}
          updateFormData={updateFormData}
          index={index}
          destinations={destinations}
        />
      )}
      {destinationType === 'multi' && (
        <Multi
          data={data}
          updateFormData={updateFormData}
          index={index}
          destinations={destinations}
        />
      )}
    </li>
  );
};

export default Destination;
