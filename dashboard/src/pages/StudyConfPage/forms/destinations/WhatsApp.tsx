import React, { useState } from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { WhatsApp as FormData, Destination } from '../../../../types/conf';
import { metadataToText, parseAdditionalMetadata } from './additionalMetadata';
import RefModeField from './RefModeField';

const TextInput = GenericTextInput as TextInputI<FormData>;

interface Props {
  data: FormData;
  updateFormData: (e: any, index: number) => void;
  index: number;
  destinations: Destination[];
}

// A click-to-WhatsApp destination. Same shape as Messenger minus button_text —
// WhatsApp has no quick-reply button, the respondent gets a prefilled compose
// box instead — and plus the phone number the ad's clicks land on.
const WhatsApp: React.FC<Props> = ({
  data,
  updateFormData,
  index,
  destinations,
}: Props) => {
  const handleChange = (e: any) => {
    const { name, value } = e.target;
    updateFormData({ ...data, [name]: value }, index);
  };

  const [metadata, setMetadata] = useState<string>(
    metadataToText(data.additional_metadata)
  );

  const handleMetadata = (e: any) => {
    const { name, value } = e.target;
    setMetadata(value);

    const result = parseAdditionalMetadata(value);
    if (result.kind === 'invalid') return;

    updateFormData(
      { ...data, [name]: result.kind === 'empty' ? null : result.value },
      index
    );
  };

  return (
    <>
      <TextInput
        name="name"
        handleChange={handleChange}
        placeholder="E.g fly whatsapp"
        value={data.name}
      />
      {/* Only letters, digits, underscore and hyphen. adopt rejects anything
          else at save time: a shortcode is shareable by design, and someone who
          texts `form.<shortcode>` into WhatsApp by hand sends a literal space,
          not %20 — which lands them in the fallback survey instead of this
          study's. */}
      <TextInput
        name="initial_shortcode"
        handleChange={handleChange}
        placeholder="E.g mnchweek (letters, digits, _ and - only)"
        value={data.initial_shortcode}
      />
      {/* Shown above the compose box on the welcome screen. Not part of the
          routing token. */}
      <TextInput
        name="welcome_message"
        handleChange={handleChange}
        placeholder="E.g Tap send to start the survey"
        value={data.welcome_message}
      />
      {/* The number itself, not the phone_number_id. Required rather than
          optional even though Meta treats it as optional: many numbers to one
          Page is supported, so omitting it silently recruits into whichever
          number happens to be "primary". */}
      <TextInput
        name="whatsapp_phone_number"
        handleChange={handleChange}
        placeholder="E.g +1-541-920-2635 (the number, not the phone_number_id)"
        value={data.whatsapp_phone_number}
      />
      <RefModeField
        refMode={data.ref_mode}
        destinations={destinations}
        handleChange={handleChange}
      />
      <TextInput
        name="additional_metadata"
        handleChange={handleMetadata}
        placeholder={`String key-value pairs e.g. {"foo": "bar"}`}
        required={false}
        value={metadata}
      />
    </>
  );
};

export default WhatsApp;
