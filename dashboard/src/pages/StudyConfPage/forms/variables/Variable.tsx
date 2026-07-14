import React, { useState, useEffect, useCallback, useRef } from 'react';
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

interface ExtractionResult {
  targeting: any;
  error: ExtractionError | null;
  lastExtractedTime: number | null;
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
  // Track extraction errors per level (by index within this variable's levels).
  // Derived from data, but kept in local state for stable rendering.
  const [levelErrors, setLevelErrors] = useState<Map<number, ExtractionError | null>>(
    new Map()
  );

  // Notify parent of error state changes.
  useEffect(() => {
    onErrorsChange?.(levelErrors);
  }, [levelErrors, onErrorsChange]);

  const update = useCallback((variableData: VariableType) => {
    updateFormData(variableData, index);
  }, [updateFormData, index]);

  const handleChange = (e: any) => {
    const { name, value } = e.target;
    update({ ...data, [name]: value });
  };

  const handleMultiSelectChange = (selected: string[]) => {
    update({ ...data, properties: selected });
  };

  // Central extraction function: given a level and properties, compute targeting,
  // error, and timestamp. This is the only place extraction happens.
  const extractLevel = useCallback((level: LevelType, properties: string[]): ExtractionResult => {
    if (!level.template_adset) {
      return { targeting: {}, error: null, lastExtractedTime: null };
    }

    const adset = adsets.find(a => a.id === level.template_adset);
    if (!adset) {
      return {
        targeting: {},
        error: { kind: 'adset_not_found', adsetName: level.template_adset },
        lastExtractedTime: null,
      };
    }

    try {
      const targeting = extractFromAdset(adset, properties);
      return { targeting, error: null, lastExtractedTime: Date.now() };
    } catch (err) {
      if (err instanceof AdsetNotFoundError) {
        return {
          targeting: {},
          error: { kind: 'adset_not_found', adsetName: err.adsetName },
          lastExtractedTime: null,
        };
      }
      if (err instanceof PropertyMissingError) {
        return {
          targeting: {},
          error: {
            kind: 'property_missing',
            adsetName: err.adsetName,
            propertyKey: err.propertyKey,
          },
          lastExtractedTime: null,
        };
      }
      throw err;
    }
  }, [adsets]);

  // Use a ref to read the latest data inside the effect without adding `data`
  // to the dependency array, which would cause unnecessary re-runs.
  const dataRef = useRef(data);
  dataRef.current = data;

  // Recompute targeting for all levels whenever inputs change.
  // Only updates lastExtractedTime when the targeting result actually changes.
  useEffect(() => {
    const currentData = dataRef.current;
    const errors = new Map<number, ExtractionError | null>();
    const newLevels = currentData.levels.map((level, levelIndex) => {
      const { targeting, error, lastExtractedTime } = extractLevel(level, currentData.properties);
      errors.set(levelIndex, error);

      const targetingChanged =
        JSON.stringify(level.facebook_targeting) !== JSON.stringify(targeting);

      return {
        ...level,
        facebook_targeting: targeting,
        template_campaign: campaignId,
        lastExtractedTime: targetingChanged
          ? lastExtractedTime
          : (level as any).lastExtractedTime || null,
      };
    });

    setLevelErrors(errors);

    const hasTargetingChanged =
      JSON.stringify(currentData.levels.map(l => l.facebook_targeting)) !==
      JSON.stringify(newLevels.map(l => l.facebook_targeting));

    if (hasTargetingChanged) {
      update({ ...currentData, levels: newLevels });
    }
  }, [data.levels, data.properties, adsets, campaignId, extractLevel, update]);

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
        }}
        data={data.levels}
        setData={setData}
        initialState={initialState}
      />

    </div>
  );
};

export default Variable;
