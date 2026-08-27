import React, { useState } from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { Messenger as FormData } from '../../../../types/conf';
import { messengerTestLink } from './messengerTestLink';

const TextInput = GenericTextInput as TextInputI<FormData>;

interface Props {
  data: FormData;
  updateFormData: (e: any, index: number) => void;
  index: number;
  // Facebook page id this destination lands on, derived from its creatives.
  // Undefined until at least one creative exists, so the test link stays hidden.
  pageId?: string;
}

const Messenger: React.FC<Props> = ({ data, updateFormData, index, pageId }: Props) => {
  const handleChange = (e: any) => {
    const { name, value } = e.target;
    updateFormData({ ...data, [name]: value }, index);
  };

  const handleMetadata = (e: any) => {
    const { name, value } = e.target;

    if (!value) {
      setMetadata(value)
      updateFormData({ ...data, [name]: null }, index)
      return
    }

    let md;

    try {
      md = JSON.parse(value)
    } catch (e) {
      setMetadata(value)
      return
    }

    setMetadata(value)
    updateFormData({ ...data, [name]: md }, index)
  }

  const additional_metadata = data.additional_metadata ? JSON.stringify(data.additional_metadata) : "";

  const [metadata, setMetadata] = useState<string>(additional_metadata);

  const testLink = messengerTestLink(pageId, data.initial_shortcode);

  return (
    <>
      <TextInput
        name="name"
        handleChange={handleChange}
        placeholder="E.g fly messenger"
        value={data.name}
      />
      <TextInput
        name="initial_shortcode"
        handleChange={handleChange}
        placeholder="E.g 12345"
        value={data.initial_shortcode}
      />
      <TextInput
        name="welcome_message"
        handleChange={handleChange}
        placeholder="E.g Welcome to our survey. Would you like to continue?"
        value={data.welcome_message}
      />
      <TextInput
        name="button_text"
        handleChange={handleChange}
        placeholder="E.g OK"
        value={data.button_text}
      />
      <TextInput
        name="additional_metadata"
        handleChange={handleMetadata}
        placeholder={`String key-value pairs e.g. {"foo": "bar"}`}
        required={false}
        value={metadata}
      />
      <div className="mt-2 mb-4 text-sm">
        {testLink ? (
          <>
            <a
              href={testLink}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 underline hover:text-blue-800"
            >
              Test this survey in Messenger →
            </a>
            <p className="mt-1 text-xs text-gray-500">
              Opens the real ad-click funnel for shortcode{' '}
              <span className="font-mono">{data.initial_shortcode}</span>. If the survey
              starts, routing works; if nothing happens, the shortcode does not resolve
              to a form.
            </p>
          </>
        ) : (
          <p className="text-xs text-gray-500">
            {data.initial_shortcode
              ? 'Add a creative to enable a Messenger test link.'
              : 'Enter a shortcode to enable a Messenger test link.'}
          </p>
        )}
      </div>
    </>
  );
};

export default Messenger;
