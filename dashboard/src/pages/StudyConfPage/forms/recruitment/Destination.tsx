import React from 'react';
import { useHistory } from 'react-router-dom';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { GenericSelect, SelectI } from '../../components/Select';
import objectives from '../../../../fixtures/general/objectives';
import destinationTypes from '../../../../fixtures/general/destinations';
import optimizationGoals from '../../../../fixtures/general/optimizationGoals';
import { RecruitmentDestination as FormData } from '../../../../types/conf';
import { Destination as DestinationType } from '../../../../types/conf';
import AddButton from '../../../../components/AddButton';
import { GenericMultiSelect, MultiSelectI } from '../../components/MultiSelect';

const TextInput = GenericTextInput as TextInputI<FormData>;
const Select = GenericSelect as SelectI<FormData>;
const MultiSelect = GenericMultiSelect as MultiSelectI<FormData>;

interface Props {
  formData: FormData;
  updateFormData: (e: any) => void;
  destinations: DestinationType[];
  studySlug: string;
}

const Destination: React.FC<Props> = ({
  formData,
  updateFormData,
  destinations,
  studySlug,
}: Props) => {
  const history = useHistory();

  const validateInput = (name: string, value: any) => {
    if (name === 'max_sample_per_arm' || name === 'budget_per_arm') {
      if (!value) {
        return parseInt('0');
      }
      return parseInt(value);
    } else return value;
  };

  const handleChange = (e: any) => {
    const { name, value } = e.target;
    updateFormData({ ...formData, [name]: validateInput(name, value) });
  };

  const handleMultiSelectChange = (selected: string[], name: string) => {
    updateFormData({ ...formData, [name]: selected });
  };

  return (
    <>
      {destinations ? (
        <MultiSelect
          name="destinations"
          options={destinations.map(d => ({ label: d.name, value: d.name }))}
          handleMultiSelectChange={handleMultiSelectChange}
          value={formData.destinations}
          label="Select the destinations in the experiment"
        ></MultiSelect>
      ) : (
        <div className="my-4">
          <label className="my-2 block text-sm font-medium text-gray-700">
            Destination
          </label>
          <AddButton
            label="Add destination"
            onClick={() => history.push(`/studies/${studySlug}/destinations`)}
          />
        </div>
      )}

      <TextInput
        name="ad_campaign_name_base"
        handleChange={handleChange}
        placeholder="E.g vlab-vaping-pilot-2"
        value={formData.ad_campaign_name_base}
      />
      <Select
        name="objective"
        options={objectives}
        handleChange={handleChange}
        value={formData.objective}
        getValue={(o: any) => o.name.toUpperCase()}
      ></Select>
      <Select
        name="optimization_goal"
        options={optimizationGoals}
        handleChange={handleChange}
        value={formData.optimization_goal}
        getValue={(o: any) => o.name.toUpperCase()}
      ></Select>
      <Select
        name="destination_type"
        options={destinationTypes}
        handleChange={handleChange}
        value={formData.destination_type}
        getValue={(o: any) => o.name.toUpperCase()}
      ></Select>
      <TextInput
        name="min_budget"
        handleChange={handleChange}
        placeholder="E.g 8400"
        value={formData.min_budget}
      />
      <TextInput
        name="budget_per_arm"
        handleChange={handleChange}
        placeholder="E.g 8400"
        value={formData.budget_per_arm}
      />
      <TextInput
        name="max_sample_per_arm"
        handleChange={handleChange}
        placeholder="E.g 1000"
        value={formData.max_sample_per_arm}
      />
      <TextInput
        name="start_date"
        type="datetime-local"
        handleChange={handleChange}
        placeholder="E.g 2022-07-26T00:00:00"
        value={formData.start_date}
      />
      <TextInput
        name="end_date"
        type="datetime-local"
        handleChange={handleChange}
        placeholder="E.g 2022-07-26T00:00:00"
        value={formData.end_date}
      />
    </>
  );
};

export default Destination;
