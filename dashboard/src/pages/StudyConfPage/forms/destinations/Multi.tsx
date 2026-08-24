import React, { useState } from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { Multi as FormData, Destination } from '../../../../types/conf';
import { metadataToText, parseAdditionalMetadata } from './additionalMetadata';
import RefModeField from './RefModeField';

const TextInput = GenericTextInput as TextInputI<FormData>;

interface Props {
  data: FormData;
  updateFormData: (e: any, index: number) => void;
  index: number;
  destinations: Destination[];
}

// One ad that opens either Messenger or WhatsApp, Meta choosing per respondent
// by predicted responsiveness. It therefore carries both arms' fields.
//
// Two things worth knowing before selecting this, both surfaced in the form:
//
//  - Its WhatsApp arm has never been observed against real delivery; it is
//    inferred from the measured Messenger arm. A wrong inference sends those
//    arrivals to the fallback survey looking like completions.
//  - Meta assigns the channel, so this cannot be used to *compare* channels.
//    A study that wants that needs two single-destination destinations in a
//    destination experiment instead.
const Multi: React.FC<Props> = ({
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
      <p className="text-sm text-gray-500 mb-2">
        One ad that opens either Messenger or WhatsApp — Meta picks per
        respondent. Requires the recruitment optimization goal to be
        CONVERSATIONS, and cannot be used to compare channels, since the channel
        is not randomised. The WhatsApp arm has not yet been verified against
        real delivery — watch its arrivals on the first study that uses it.
      </p>
      <TextInput
        name="name"
        handleChange={handleChange}
        placeholder="E.g fly multi"
        value={data.name}
      />
      {/* One shortcode for both arms, never one per channel: there is exactly
          one attribution row per ad, and a per-channel shortcode would mean one
          ad whose two arms belong to two different surveys. */}
      <TextInput
        name="initial_shortcode"
        handleChange={handleChange}
        placeholder="E.g mnchweek (letters, digits, _ and - only)"
        value={data.initial_shortcode}
      />
      <TextInput
        name="welcome_message"
        handleChange={handleChange}
        placeholder="E.g Tap below or send to start the survey"
        value={data.welcome_message}
      />
      {/* The Messenger arm's quick-reply button. Required: it is the only
          routing carrier for 68% of Messenger ad entrants. */}
      <TextInput
        name="button_text"
        handleChange={handleChange}
        placeholder="E.g Start survey (the Messenger arm's button)"
        value={data.button_text}
      />
      <TextInput
        name="whatsapp_phone_number"
        handleChange={handleChange}
        placeholder="E.g +1-541-920-2635 (the number, not the phone_number_id)"
        value={data.whatsapp_phone_number}
      />
      <RefModeField refMode={data.ref_mode} handleChange={handleChange} />
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

export default Multi;
