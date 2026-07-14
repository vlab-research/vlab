import React, { useState } from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { GenericSelect, SelectI } from '../../components/Select';
import { Level as FormData } from '../../../../types/conf';
import { renderTargetingSummary } from '../shared/TargetingSummary';
import type { ExtractionError } from './Variable';

const TextInput = GenericTextInput as TextInputI<FormData>;
const Select = GenericSelect as SelectI<FormData>;

interface Props {
  data: any;
  index: number;
  adsets: any[];
  update: (d: any, index: number) => void;
  levelErrors?: Map<string, ExtractionError | null>;
  variableIndex: number;
  properties?: string[];
}

const Level: React.FC<Props> = ({
  adsets,
  data,
  index,
  update: handleChange,
  levelErrors,
  variableIndex,
  properties,
}: Props) => {
  const [showRawJson, setShowRawJson] = useState(false);

  const error = levelErrors?.get(`${variableIndex}:${index}`);
  const lastExtractedTime = (data as any).lastExtractedTime as number | null | undefined;
  const lastExtractedAdset = (data as any).lastExtractedAdset as string | null | undefined;
  const lastExtractedProperties = (data as any).lastExtractedProperties as string[] | null | undefined;

  const onChange = (e: any) => {
    const { name, value } = e.target;
    handleChange({ ...data, [name]: value }, index);
  };

  const onAdsetChange = (e: any) => {
    const adsetId = e.target.value;
    handleChange({ ...data, template_adset: adsetId }, index);
  };

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

  const hasTargeting =
    data.facebook_targeting && Object.keys(data.facebook_targeting).length > 0;

  const adsetStale = data.template_adset !== lastExtractedAdset;
  const propertiesStale =
    JSON.stringify(properties || []) !==
    JSON.stringify(lastExtractedProperties || []);
  const isStale = !hasTargeting || adsetStale || propertiesStale;

  const sourceAdset = adsets.find(a => a.id === data.template_adset);
  const sourceTA = sourceAdset?.targeting?.targeting_automation;
  const sourceAdvantageOn = sourceTA?.advantage_audience === 1;
  const sourceControls = sourceTA?.individual_setting
    ? Object.entries(sourceTA.individual_setting)
        .filter(([, v]: [string, any]) => v === 1)
        .map(([k]: [string, any]) => k)
    : [];

  return (
    <li>
      <div className="m-4 border-b pb-4">
        <TextInput
          name="name"
          handleChange={onChange}
          autoComplete="on"
          placeholder="Give your level a name"
          value={data.name}
          data-testid="level-name-input"
        />
        <Select
          name="template_adset"
          options={adsets}
          handleChange={onAdsetChange}
          value={data.template_adset}
          getValue={(o: any) => o.id}
          data-testid="level-adset-select"
        ></Select>
        <TextInput
          name="quota"
          handleChange={onChange}
          placeholder="Give your a quota"
          value={data.quota}
        />

        {error && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700" data-testid="level-error">
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

        {isStale && !error && (
          <div
            className="mt-3 p-3 bg-amber-50 border border-amber-300 rounded text-sm text-amber-800"
            data-testid="level-stale-badge"
          >
            {!hasTargeting ? (
              <span>Not yet extracted — click Refresh from Meta to pull targeting from the template adset.</span>
            ) : (
              <span>Stale — targeting may not match current adset/properties. Click Refresh from Meta to update.</span>
            )}
          </div>
        )}

        <div className="mt-3 p-3 bg-gray-50 border border-gray-200 rounded" data-testid="level-output-panel">
          <div className="text-xs font-semibold text-gray-600 mb-2">Output</div>
          <div className="text-sm mb-2" data-testid="level-targeting-summary">
            {renderTargetingSummary(data.facebook_targeting)}
          </div>

          {sourceAdset && (
            <div
              className={
                sourceAdvantageOn
                  ? 'mt-3 p-3 bg-amber-50 border border-amber-300 rounded text-xs space-y-1'
                  : 'mt-3 p-3 bg-gray-100 border border-gray-200 rounded text-xs space-y-1'
              }
              data-testid="level-advantage-callout"
            >
              <div className="font-semibold text-gray-700">Advantage+ Audience</div>
              <div>
                <span className="text-gray-500">Source adset:</span>{' '}
                {sourceAdvantageOn ? (
                  <span className="text-amber-700 font-medium">
                    Enabled
                    {sourceControls.length > 0 && ` (controls: ${sourceControls.join(', ')})`}
                  </span>
                ) : sourceTA ? (
                  <span className="text-gray-600">Disabled</span>
                ) : (
                  <span className="text-gray-400 italic">Not set</span>
                )}
              </div>
              <div>
                <span className="text-gray-500">Applied:</span>{' '}
                <span className="text-gray-700 font-medium">Disabled</span>
              </div>
              {sourceAdvantageOn && (
                <div className="text-gray-500 pt-1">
                  Overridden — targeting uses only the properties you select, not Meta's
                  audience expansion. This avoids Advantage+ constraints (e.g. age_min ≤ 25).
                </div>
              )}
            </div>
          )}

          <button
            type="button"
            onClick={() => setShowRawJson(!showRawJson)}
            data-testid="level-toggle-json"
            className="text-xs text-blue-600 hover:underline mb-2"
          >
            {showRawJson ? '▼ Hide JSON' : '▶ Show JSON'}
          </button>
          {showRawJson && (
            <pre className="bg-white p-2 rounded border border-gray-300 text-xs overflow-auto max-h-40">
              {JSON.stringify(data.facebook_targeting, null, 2)}
            </pre>
          )}
          {lastExtractedTime && !isStale && (
            <div className="text-xs text-gray-500 mt-2" data-testid="level-last-extracted">
              Last extracted: {formatRelativeTime(lastExtractedTime)}
            </div>
          )}
        </div>
      </div>
    </li>
  );
};

export default Level;
