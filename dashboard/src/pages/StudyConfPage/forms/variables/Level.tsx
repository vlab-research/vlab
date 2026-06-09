import React, { useState, useEffect } from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { GenericSelect, SelectI } from '../../components/Select';
import { Level as FormData } from '../../../../types/conf';
import { extractFromAdset, AdsetNotFoundError, PropertyMissingError } from './extract';
import { renderTargetingSummary } from '../shared/TargetingSummary';
import type { ExtractionError } from './Variable';

const TextInput = GenericTextInput as TextInputI<FormData>;
const Select = GenericSelect as SelectI<FormData>;

interface Props {
  data: any;
  index: number;
  adsets: any[];
  properties: string[];
  update: (d: any, index: number) => void;
  levelErrors?: Map<number, ExtractionError | null>;
  reExtractLevel?: (levelIndex: number, levelData: any) => any;
}

const Level: React.FC<Props> = ({
  adsets,
  data,
  index,
  update: handleChange,
  properties,
  levelErrors,
  reExtractLevel,
}: Props) => {
  const [lastExtractedTime, setLastExtractedTime] = useState<number | null>(null);
  const [showRawJson, setShowRawJson] = useState(false);

  const error = levelErrors?.get(index);

  const onChange = (e: any) => {
    const { name, value } = e.target;
    handleChange({ ...data, [name]: value }, index);
  };

  const onAdsetChange = (e: any) => {
    const adsetId = e.target.value;
    const adset = adsets.find(a => a.id === adsetId);

    try {
      const extracted = extractFromAdset(adset, properties);
      handleChange(
        { ...data, facebook_targeting: extracted, template_adset: adsetId },
        index
      );
      setLastExtractedTime(Date.now());
    } catch (err) {
      // reExtractLevel in the parent (Variable.tsx) will handle errors and update state
      // We still update the adset selection even if extraction fails, so the UI reflects the user's choice
      handleChange(
        { ...data, facebook_targeting: {}, template_adset: adsetId },
        index
      );
    }
  };

  // Format relative time (e.g. "2 minutes ago")
  const formatRelativeTime = (timestamp: number) => {
    const seconds = Math.floor((Date.now() - timestamp) / 1000);
    if (seconds < 60) return 'just now';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  };


  return (
    <li>
      <div className="m-4 border-b pb-4">
        {/* Input controls */}
        <TextInput
          name="name"
          handleChange={onChange}
          autoComplete="on"
          placeholder="Give your level a name"
          value={data.name}
        />
        <Select
          name="template_adset"
          options={adsets}
          handleChange={onAdsetChange}
          value={data.template_adset}
          getValue={(o: any) => o.id}
        ></Select>
        <TextInput
          name="quota"
          handleChange={onChange}
          placeholder="Give your a quota"
          value={data.quota}
        />

        {/* Error display */}
        {error && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
            {error.kind === 'adset_not_found' ? (
              <div>
                Template adset <strong>{error.adsetName}</strong> not found on Meta — pick a different
                adset or fix on Meta.
              </div>
            ) : (
              <div>
                Adset <strong>{error.adsetName}</strong> has no <code>{error.propertyKey}</code> property.
              </div>
            )}
          </div>
        )}

        {/* Output panel */}
        <div className="mt-3 p-3 bg-gray-50 border border-gray-200 rounded">
          <div className="text-xs font-semibold text-gray-600 mb-2">Output</div>
          <div className="text-sm mb-2">
            {renderTargetingSummary(data.facebook_targeting)}
          </div>
          <button
            type="button"
            onClick={() => setShowRawJson(!showRawJson)}
            className="text-xs text-blue-600 hover:underline mb-2"
          >
            {showRawJson ? '▼ Hide JSON' : '▶ Show JSON'}
          </button>
          {showRawJson && (
            <pre className="bg-white p-2 rounded border border-gray-300 text-xs overflow-auto max-h-40">
              {JSON.stringify(data.facebook_targeting, null, 2)}
            </pre>
          )}
          {lastExtractedTime && (
            <div className="text-xs text-gray-500 mt-2">
              Last extracted: {formatRelativeTime(lastExtractedTime)}
            </div>
          )}
        </div>
      </div>
    </li>
  );
};

export default Level;
