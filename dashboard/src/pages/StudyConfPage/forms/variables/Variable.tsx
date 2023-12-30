import React from 'react';
import AddButton from '../../../../components/AddButton';
import DeleteButton from '../../../../components/DeleteButton';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { GenericMultiSelect, MultiSelectI } from '../../components/MultiSelect';
import Level from './Level';
import { classNames } from '../../../../helpers/strings';
import { Variable as FormData } from '../../../../types/conf';
import {
  Level as LevelType,
  Variable as VariableType,
} from '../../../../types/conf';


const TextInput = GenericTextInput as TextInputI<FormData>;
const MultiSelect = GenericMultiSelect as MultiSelectI<FormData>;

interface Props {
  data: VariableType;
  index: number;
  adsets: any[];
  campaignId: string;
  update: (d: any, index: number) => void;
}

const Variable: React.FC<Props> = ({
  data,
  index,
  adsets,
  campaignId,
  update: updateFormData,
}: Props) => {
  // Function to help get targeting params out of adset
  const getTargeting = (data: any, adsetId: string) => {
    if (!adsetId) return {};
    const adset = adsets.find(a => adsetId === a.id);

    if (!adset) {
      return {};
    }

    return data.properties.reduce(
      (obj: any, key: string) => ({ ...obj, [key]: adset.targeting[key] }),
      {}
    );
  };

  const reformulateData = (data: VariableType) => {
    data['levels'] = data.levels.map((l: any) => ({
      ...l,
      facebook_targeting: getTargeting(data, l.template_adset),
      template_campaign: campaignId,
    }));
    return data;
  };

  // Make sure all levels are current on each render
  data = reformulateData(data);

  const update = (data: any) => {
    const d = reformulateData(data);
    updateFormData(d, index);
  };

  const handleChange = (e: any) => {
    const { name, value } = e.target;
    update({ ...data, [name]: value });
  };

  const handleLevelChange = (d: any, i: number) => {
    const copy = [...data.levels];
    copy[i] = { ...copy[i], ...d };
    update({ ...data, levels: copy });
  };

  const handleMultiSelectChange = (selected: string[], name: string) => {
    update({ ...data, [name]: selected });
  };

  const addLevel = (): void => {
    const level: LevelType = {
      name: '',
      template_adset: adsets[0]?.id,
      template_campaign: campaignId,
      facebook_targeting: getTargeting(data, adsets[0]?.id),
      quota: 0,
    };

    update({ ...data, levels: [...data.levels, level] });
  };

  const deleteLevel = (i: number): void => {
    const newArr = data.levels.filter((_: any, ii: number) => ii !== i);
    update({ ...data, levels: [...newArr] });
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
      />
      <MultiSelect
        name="properties"
        options={properties.map((p: any) => ({ label: p.label, value: p.name }))}
        handleMultiSelectChange={handleMultiSelectChange}
        value={data.properties}
        label="Select a set of properties from Facebook"
      ></MultiSelect>
      <ul>
        {data.levels?.map((l: any, levelIndex: number) => {
          return (
            <div key={levelIndex}>
              <Level
                data={l}
                adsets={adsets}
                properties={data.properties}
                index={levelIndex}
                handleChange={handleLevelChange}
              ></Level>

              <div className="flex flex-row w-4/5 justify-between items-center">
                <div className="w-4/5 h-0.5 mr-8 my-4 rounded-md bg-gray-400"></div>
                <DeleteButton
                  onClick={() => deleteLevel(levelIndex)}
                ></DeleteButton>
              </div>
              <div />
            </div>
          );
        })}
      </ul>
      <div className="flex flex-row items-center mb-4">
        <AddButton onClick={addLevel} label="Add a level" />
      </div>
    </div>
  );
};

export default Variable;
