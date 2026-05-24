import React, { useState } from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { GenericMultiSelect, MultiSelectI } from '../../components/MultiSelect';
import { Stratum as FormData, Creative as CreativeType } from '../../../../types/conf';
import { renderTargetingSummary } from '../shared/TargetingSummary';

const TextInput = GenericTextInput as TextInputI<FormData>;
const MultiSelect = GenericMultiSelect as MultiSelectI<FormData>;

const Stratum: React.FC<{
  stratum: FormData;
  creatives: CreativeType[];
  onChange: (e: any) => void;
}> = ({ stratum, onChange, creatives }) => {
  const [showRawJson, setShowRawJson] = useState(false);

  const handleMultiSelectChange = (selected: string[], name: string) => {
    onChange({ target: { name, value: selected } });
  };

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

      {/* Output panel */}
      <div className="mt-3 p-3 bg-gray-50 border border-gray-200 rounded">
        <div className="text-xs font-semibold text-gray-600 mb-2">Output</div>

        {/* Targeting summary */}
        <div className="text-sm mb-3">
          <div className="font-semibold text-gray-700 mb-1">Facebook Targeting:</div>
          {renderTargetingSummary(stratum.facebook_targeting)}
        </div>

        {/* Expandable raw JSON */}
        <button
          type="button"
          onClick={() => setShowRawJson(!showRawJson)}
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
