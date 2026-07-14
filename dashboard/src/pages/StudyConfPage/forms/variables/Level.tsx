import React, { useState, useMemo } from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { GenericSelect, SelectI } from '../../components/Select';
import { Level as FormData } from '../../../../types/conf';
import { renderTargetingSummary } from '../shared/TargetingSummary';
import type { ExtractionError } from './Variable';
import {
  extractFromAdset,
  AdsetNotFoundError,
  PropertyMissingError,
  isLevelInSync,
  diffPropertyKeys,
} from './extract';

const TextInput = GenericTextInput as TextInputI<FormData>;
const Select = GenericSelect as SelectI<FormData>;

interface Props {
  data: any;
  index: number;
  adsets: any[];
  update: (d: any, index: number) => void;
  properties: string[];
}

const Level: React.FC<Props> = ({
  adsets,
  data,
  index,
  update: handleChange,
  properties,
}: Props) => {
  const [showRawJson, setShowRawJson] = useState(false);

  const onChange = (e: any) => {
    const { name, value } = e.target;
    handleChange({ ...data, [name]: value }, index);
  };

  const onAdsetChange = (e: any) => {
    const adsetId = e.target.value;
    handleChange({ ...data, template_adset: adsetId }, index);
  };

  const computed = useMemo(() => {
    try {
      const adset = adsets.find((a: any) => a.id === data.template_adset);
      const wouldApply = extractFromAdset(adset, properties || []);
      return { error: null as ExtractionError | null, wouldApply };
    } catch (err) {
      if (err instanceof AdsetNotFoundError) {
        return {
          error: { kind: 'adset_not_found', adsetName: err.adsetName } as ExtractionError,
          wouldApply: null,
        };
      }
      if (err instanceof PropertyMissingError) {
        return {
          error: {
            kind: 'property_missing',
            adsetName: err.adsetName,
            propertyKey: err.propertyKey,
          } as ExtractionError,
          wouldApply: null,
        };
      }
      throw err;
    }
  }, [adsets, data.template_adset, properties]);

  const inSync = !computed.error && isLevelInSync(data.facebook_targeting, computed.wouldApply);
  const keyDiff = diffPropertyKeys(data.facebook_targeting, properties || []);

  const sourceAdset = adsets.find((a: any) => a.id === data.template_adset);
  const sourceAdvantageOn = sourceAdset?.targeting?.targeting_automation?.advantage_audience === 1;

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

        {computed.error && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700" data-testid="level-error">
            {computed.error.kind === 'adset_not_found' ? (
              <div>
                Template adset <strong>{computed.error.adsetName}</strong> not found on Meta — pick a different
                adset or fix on Meta.
              </div>
            ) : (
              <div>
                Adset <strong>{computed.error.adsetName}</strong> has no <code>{computed.error.propertyKey}</code> property.
              </div>
            )}
          </div>
        )}

        {!computed.error && !inSync && (
          <div
            className="mt-3 p-3 bg-amber-50 border border-amber-300 rounded text-sm text-amber-800"
            data-testid="level-out-of-sync-banner"
          >
            {keyDiff.keysDiffer ? (
              <>
                <div>
                  Properties changed: added {keyDiff.added.join(', ') || '(none)'}, removed {keyDiff.removed.join(', ') || '(none)'}.
                </div>
                <div>
                  Apply on the variable above to use your current selections.
                </div>
              </>
            ) : (
              <div>
                Out of sync with current Meta data — Apply on the variable above to use your current selections.
              </div>
            )}
          </div>
        )}

        <div className="mt-3 p-3 bg-gray-50 border border-gray-200 rounded" data-testid="level-output-panel">
          <div className="text-xs font-semibold text-gray-600 mb-2">Output</div>
          <div className="text-sm mb-2" data-testid="level-targeting-summary">
            {renderTargetingSummary(data.facebook_targeting)}
          </div>

          {sourceAdvantageOn && (
            <div className="mt-2 text-xs text-gray-500" data-testid="level-advantage-note">
              Advantage+ Audience was enabled on the source adset but is disabled here.
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
        </div>
      </div>
    </li>
  );
};

export default Level;
