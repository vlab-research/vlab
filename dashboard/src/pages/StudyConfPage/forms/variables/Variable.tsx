import React, { useState, useCallback, useEffect } from 'react';
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
import { extractFromAdset, AdsetNotFoundError, PropertyMissingError } from './extract';

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
  onErrorsChange?: (errors: Map<number, ExtractionError | null>) => void;
}

const Variable: React.FC<Props> = ({
  data,
  index,
  adsets,
  campaignId,
  update: updateFormData,
  onErrorsChange,
}: Props) => {
  // Track extraction errors per level (by index within this variable's levels)
  const [levelErrors, setLevelErrors] = useState<Map<number, ExtractionError | null>>(
    new Map()
  );

  // Notify parent of error state changes
  useEffect(() => {
    onErrorsChange?.(levelErrors);
  }, [levelErrors, onErrorsChange]);

  // Re-extract for a single level using the provided properties.
  // Properties are passed as an argument so property changes (including unselecting)
  // recompute targeting with the current selection instead of a stale closure.
  const reExtractLevel = useCallback(
    (levelIndex: number, levelData: LevelType, properties: string[]) => {
      if (!levelData.template_adset) {
        // No adset selected; clear any existing error
        setLevelErrors(prev => {
          const next = new Map(prev);
          next.delete(levelIndex);
          return next;
        });
        return { ...levelData, facebook_targeting: {} };
      }

      const adset = adsets.find(a => a.id === levelData.template_adset);

      try {
        const extracted = extractFromAdset(adset, properties);
        // Success: clear the error and update targeting
        setLevelErrors(prev => {
          const next = new Map(prev);
          next.delete(levelIndex);
          return next;
        });
        return { ...levelData, facebook_targeting: extracted, template_campaign: campaignId };
      } catch (err) {
        if (err instanceof AdsetNotFoundError) {
          const error: ExtractionError = {
            kind: 'adset_not_found',
            adsetName: err.adsetName,
          };
          setLevelErrors(prev => new Map(prev).set(levelIndex, error));
          return { ...levelData, facebook_targeting: {}, template_campaign: campaignId };
        } else if (err instanceof PropertyMissingError) {
          const error: ExtractionError = {
            kind: 'property_missing',
            adsetName: err.adsetName,
            propertyKey: err.propertyKey,
          };
          setLevelErrors(prev => new Map(prev).set(levelIndex, error));
          return { ...levelData, facebook_targeting: {}, template_campaign: campaignId };
        }
        throw err;
      }
    },
    [adsets, campaignId]
  );

  const update = (data: VariableType) => {
    updateFormData(data, index);
  };

  const handleChange = (e: any) => {
    const { name, value } = e.target;
    update({ ...data, [name]: value });
  };

  const handleMultiSelectChange = (selected: string[], name: string) => {
    // When properties change, re-extract for all levels using the new selection.
    const updatedData = { ...data, [name]: selected };
    const newLevels = updatedData.levels.map((level, levelIndex) => {
      return reExtractLevel(levelIndex, level, selected);
    });
    update({ ...updatedData, levels: newLevels });
  };

  const initialState: LevelType[] = [{
    name: '',
    template_adset: adsets[0]?.id,
    template_campaign: campaignId,
    facebook_targeting: {},
    quota: 0,
  }]

  const setData = (a: LevelType[]) => {
    update({ ...data, levels: a })
  }

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
        elementProps={{ adsets: adsets, properties: data.properties, levelErrors, reExtractLevel }}
        data={data.levels}
        setData={setData}
        initialState={initialState}
      />

    </div>
  );
};

export default Variable;
