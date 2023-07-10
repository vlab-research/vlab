import React, { useEffect } from 'react';
import { Path } from 'react-hook-form';
import { classNames } from '../../../../helpers/strings';
import AddButton from '../../../../components/AddButton';
import { Level as LevelType } from '../../../../types/conf';
import Level, { TextInput } from './Level';
import DeleteButton from '../../../../components/DeleteButton';

export interface FormData {
  name: string;
  properties: string[];
  levels: any[];
}

interface MultiSelectProps {
  name: Path<FormData>;
  options: SelectOption[];
  handleMultiSelectChange: (selectedValues: string[], name: string) => void;
  value: string[];
  label: string;
}

interface SelectOption {
  name: string;
  label: string;
}

const MultiSelect: React.FC<MultiSelectProps> = ({
  name,
  options,
  handleMultiSelectChange,
  value,
  label,
}: MultiSelectProps) => {
  const onChange = (e: any) => {
    const selected = Array.from(e.target.selectedOptions).map(
      (option: any) => option.value
    );
    handleMultiSelectChange(selected, name);
  };

  return (
    <div className="sm:my-4">
      <label className="my-2 block text-sm font-medium text-gray-700">
        {label}
      </label>
      <select
        multiple
        value={value}
        onChange={onChange}
        className="w-4/5 block shadow-sm sm:text-sm rounded-md"
      >
        {options.map((option: SelectOption, i: number) => (
          <option
            key={i}
            value={option.name}
            className="px-4 py-2 text-gray-700 sm:text-sm rounded-md cursor-pointer hover:text-gray-900 hover:bg-gray-100 transition duration-300 ease-in-out focus:outline-none"
          >
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
};

interface Props {
  data: any;
  formData: any[];
  index: number;
  adsets: any[];
  campaignId: string;
  updateFormData: (d: any, index: number) => void;
}

const Variable: React.FC<Props> = ({
  data,
  formData,
  index,
  adsets,
  campaignId,
  updateFormData,
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

  // update will always update targeting to keep it current
  const update = (data: any) => {
    data['levels'] = data.levels.map((l: any) => ({
      ...l,
      facebook_targeting: getTargeting(data, l.template_adset),
      template_campaign: campaignId,
    }));
    updateFormData(data, index);
  };

  // trigger update on campaignId change
  useEffect(() => {
    update(data);
  }, [campaignId]);

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
  ];

  return (
    <div className={classNames(index === 0 ? 'mt-4' : 'mt-8')}>
      <TextInput
        name="name"
        type="text"
        handleChange={handleChange}
        required
        autoComplete="on"
        placeholder="Give your variable a name"
        value={data.name}
      />
      <MultiSelect
        name="properties"
        options={properties}
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
        <AddButton onClick={addLevel} />
        <span className="ml-4 italic text-gray-700 text-sm">Add a level</span>
      </div>
    </div>
  );
};

export default Variable;
