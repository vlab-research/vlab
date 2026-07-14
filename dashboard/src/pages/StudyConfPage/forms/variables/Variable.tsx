import React from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { GenericMultiSelect, MultiSelectI } from '../../components/MultiSelect';
import Level from './Level';
import { classNames } from '../../../../helpers/strings';
import { Variable as FormData } from '../../../../types/conf';
import {
  Level as LevelType,
  Variable as VariableType,
} from '../../../../types/conf';
import { GenericListFactory } from '../../components/GenericList';
import { extractFromAdset } from './extract';

const LevelList = GenericListFactory<LevelType>();
const TextInput = GenericTextInput as TextInputI<FormData>;
const MultiSelect = GenericMultiSelect as MultiSelectI<FormData>;

export interface ExtractionError {
  kind: 'adset_not_found' | 'property_missing';
  adsetName: string;
  propertyKey?: string;
}

interface Props {
  data: VariableType;
  index: number;
  adsets: any[];
  campaignId: string;
  update: (d: any, index: number) => void;
  metaIsLoading: boolean;
  metaIsError: boolean;
}

const PROPERTY_OPTIONS = [
  { name: 'genders', label: 'Genders' },
  { name: 'age_min', label: 'Minimum age' },
  { name: 'age_max', label: 'Maximum age' },
  { name: 'geo_locations', label: 'Geo Locations' },
  { name: 'excluded_geo_locations', label: 'Excluded Geo Locations' },
  { name: 'flexible_spec', label: 'Flexible Spec' },
  { name: 'custom_audiences', label: 'Custom Audiences' },
  { name: 'excluded_custom_audiences', label: 'Excluded Custom Audiences' },
];

const Variable: React.FC<Props> = ({
  data,
  index,
  adsets,
  campaignId,
  update: updateFormData,
  metaIsLoading,
  metaIsError,
}: Props) => {
  const update = (variableData: VariableType) => {
    updateFormData(variableData, index);
  };

  const handleChange = (e: any) => {
    const { name, value } = e.target;
    update({ ...data, [name]: value });
  };

  const handleMultiSelectChange = (selected: string[]) => {
    update({ ...data, properties: selected });
  };

  const initialState: LevelType[] = [{
    name: '',
    template_adset: adsets[0]?.id,
    template_campaign: campaignId,
    facebook_targeting: {},
    quota: 0,
  }];

  const setData = (levels: LevelType[]) => {
    update({ ...data, levels });
  };

  const computeApplyDisabledReason = (): string | null => {
    if (metaIsLoading) return 'Waiting for Meta cache…';
    if (metaIsError) return 'Meta cache unavailable — refresh to retry.';
    if (data.properties.length === 0) return 'Select properties above to enable Apply.';
    if (data.levels.length === 0) return 'Add a level below to enable Apply.';
    return null;
  };

  const handleApply = () => {
    const updatedLevels = data.levels.map(level => {
      const adset = adsets.find((a: any) => a.id === level.template_adset);
      try {
        const extracted = extractFromAdset(adset, data.properties);
        return { ...level, facebook_targeting: extracted };
      } catch {
        return { ...level, facebook_targeting: {} };
      }
    });
    update({ ...data, levels: updatedLevels });
  };

  const disabledReason = computeApplyDisabledReason();

  return (
    <div className={classNames(index === 0 ? 'mt-4' : 'mt-8')}>
      <TextInput
        name="name"
        handleChange={handleChange}
        required
        autoComplete="on"
        placeholder="Give your variable a name"
        value={data.name}
        data-testid="variable-name-input"
      />
      <MultiSelect
        name="properties"
        options={PROPERTY_OPTIONS.map((p: any) => ({ label: p.label, value: p.name }))}
        handleMultiSelectChange={handleMultiSelectChange}
        value={data.properties}
        label="Select a set of properties from Facebook"
        data-testid="variable-properties-select"
      ></MultiSelect>
      <div className="mt-2 flex items-center gap-3" data-testid="variable-apply-row">
        <button
          type="button"
          onClick={handleApply}
          disabled={disabledReason !== null}
          data-testid="variable-apply-button"
          className="px-4 py-2 bg-blue-600 text-white rounded font-medium hover:bg-blue-700 disabled:bg-gray-400"
        >
          Apply
        </button>
        {disabledReason && (
          <span className="text-sm text-gray-500" data-testid="variable-apply-reason">
            {disabledReason}
          </span>
        )}
      </div>
      <LevelList
        Element={Level}
        elementName="level"
        elementProps={{
          adsets,
          properties: data.properties,
        }}
        data={data.levels}
        setData={setData}
        initialState={initialState}
      />
    </div>
  );
};

export default Variable;
