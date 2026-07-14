import React, { useState } from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { GenericMultiSelect, MultiSelectI } from '../../components/MultiSelect';
import { Stratum as FormData, Creative as CreativeType, Audience as AudienceType } from '../../../../types/conf';
import { renderTargetingSummary } from '../shared/TargetingSummary';

const TextInput = GenericTextInput as TextInputI<FormData>;
const MultiSelect = GenericMultiSelect as MultiSelectI<FormData>;

const Stratum: React.FC<{
  stratum: FormData;
  creatives: CreativeType[];
  audiences: AudienceType[];
  onChange: (e: any) => void;
}> = ({ stratum, onChange, creatives, audiences }) => {
  const [showRawJson, setShowRawJson] = useState(false);

  const handleMultiSelectChange = (selected: string[], name: string) => {
    onChange({ target: { name, value: selected } });
  };

  const toggleAudience = (audienceName: string, field: 'audiences' | 'excluded_audiences') => {
    const current = stratum[field];
    const updated = current.includes(audienceName)
      ? current.filter((n: string) => n !== audienceName)
      : [...current, audienceName];
    onChange({ target: { name: field, value: updated } });
  };

  const isAudienceExcluded = (name: string) => stratum.excluded_audiences.includes(name);
  const isAudienceIncluded = (name: string) => stratum.audiences.includes(name);

  return (
    <li>
      <TextInput
        name="id"
        value={stratum.id}
        disabled={true}
        placeholder="name"
        handleChange={onChange}
      />
      <TextInput
        name="quota"
        value={stratum.quota}
        placeholder="Give your stratum a quota e.g 5"
        handleChange={onChange}
      />
      <MultiSelect
        name="creatives"
        options={creatives.map(c => ({ label: c.name, value: c.name }))}
        handleMultiSelectChange={handleMultiSelectChange}
        value={stratum.creatives}
        label="Select a set of creatives for this stratum"
      ></MultiSelect>

      {audiences.length > 0 && (
        <div className="sm:my-4">
          <label className="my-2 block text-sm font-medium text-gray-700">
            Excluded Audiences
          </label>
          <div className="flex flex-col space-y-1">
            {audiences.map(a => (
              <label key={a.name} className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isAudienceExcluded(a.name)}
                  onChange={() => toggleAudience(a.name, 'excluded_audiences')}
                  className="rounded text-indigo-600"
                />
                <span className="text-sm text-gray-700">{a.name}</span>
              </label>
            ))}
          </div>
        </div>
      )}

      {audiences.length > 0 && (
        <div className="sm:my-4">
          <label className="my-2 block text-sm font-medium text-gray-700">
            Included Audiences
          </label>
          <div className="flex flex-col space-y-1">
            {audiences.map(a => (
              <label key={a.name} className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isAudienceIncluded(a.name)}
                  onChange={() => toggleAudience(a.name, 'audiences')}
                  className="rounded text-indigo-600"
                />
                <span className="text-sm text-gray-700">{a.name}</span>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Output panel */}
      <div className="mt-3 p-3 bg-gray-50 border border-gray-200 rounded" data-testid="stratum-output-panel">
        <div className="text-xs font-semibold text-gray-600 mb-2">Output</div>

        {/* Targeting summary */}
        <div className="text-sm mb-3" data-testid="stratum-targeting-summary">
          <div className="font-semibold text-gray-700 mb-1">Facebook Targeting:</div>
          {renderTargetingSummary(stratum.facebook_targeting)}
        </div>

        {/* Expandable raw JSON */}
        <button
          type="button"
          onClick={() => setShowRawJson(!showRawJson)}
          data-testid="stratum-toggle-json"
          className="text-xs text-blue-600 hover:underline mb-2"
        >
          {showRawJson ? '▼ Hide JSON' : '▶ Show JSON'}
        </button>
        {showRawJson && (
          <pre className="bg-white p-2 rounded border border-gray-300 text-xs overflow-auto max-h-40 mb-3">
            {JSON.stringify(stratum.facebook_targeting, null, 2)}
          </pre>
        )}

        {/* Compact summary of per-stratum edits */}
        <div className="text-xs text-gray-600 space-y-1">
          <div>Creatives: {stratum.creatives?.length || 0}</div>
          <div>Audiences: {stratum.audiences?.length || 0}</div>
          <div>Excluded Audiences: {stratum.excluded_audiences?.length || 0}</div>
          <div>Quota: {stratum.quota || '—'}</div>
        </div>
      </div>

      <div className="w-4/5 h-0.5 mr-8 my-6 rounded-md bg-gray-400"></div>
    </li>
  );
};

export default Stratum;
