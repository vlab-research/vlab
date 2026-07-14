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
  levelErrors?: Map<string, ExtractionError | null>;
}

const Variable: React.FC<Props> = ({
  data,
  index,
  adsets,
  campaignId,
  update: updateFormData,
  levelErrors,
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

  const properties = [
    { name: 'genders', label: 'Genders' },
    { name: 'age_min', label: 'Minimum age' },
    { name: 'age_max', label: 'Maximum age' },
    { name: 'geo_locations', label: 'Geo Locations' },
    { name: 'excluded_geo_locations', label: 'Excluded Geo Locations' },
    { name: 'flexible_spec', label: 'Flexible Spec' },
    { name: 'custom_audiences', label: 'Custom Audiences' },
    { name: 'excluded_custom_audiences', label: 'Excluded Custom Audiences' },
  ];

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
        options={properties.map((p: any) => ({ label: p.label, value: p.name }))}
        handleMultiSelectChange={handleMultiSelectChange}
        value={data.properties}
        label="Select a set of properties from Facebook"
        data-testid="variable-properties-select"
      ></MultiSelect>
      <LevelList
        Element={Level}
        elementName="level"
        elementProps={{
          adsets,
          levelErrors,
          variableIndex: index,
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
