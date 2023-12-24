import React from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { PipelineExperiment as FormData } from '../../../../types/conf';
import objectives from '../../../../fixtures/general/objectives';
import destinationTypes from '../../../../fixtures/general/destinations';
import optimizationGoals from '../../../../fixtures/general/optimizationGoals';
import { GenericSelect, SelectI } from '../../components/Select';
const Select = GenericSelect as SelectI<FormData>;
const TextInput = GenericTextInput as TextInputI<FormData>;

interface Props {
  formData: FormData;
  updateFormData: (e: any) => void;
}

const validateInput = (name: string, value: any) => {
  if (
    name === 'budget_per_arm' ||
    name === 'max_sample_per_arm' ||
    name === 'arms' ||
    name === 'recruitment_days' ||
    name === 'offset_days'
  ) {
    if (!value) {
      return parseInt('0');
    }
    return parseInt(value);
  } else return value;
};

const PipelineExperiment: React.FC<Props> = ({
  formData,
  updateFormData,
}: Props) => {
  const handleChange = (e: any) => {
    const { name, value } = e.target;
    updateFormData({ ...formData, [name]: validateInput(name, value) });
  };

  return (
    <>
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
        handleChange={handleChange}
        placeholder="E.g 2022-07-26T00:00:00"
        value={formData.start_date}
      />
      <TextInput
        name="end_date"
        handleChange={handleChange}
        placeholder="E.g 2022-07-26T00:00:00"
        value={formData.end_date}
      />
      <TextInput
        name="arms"
        handleChange={handleChange}
        placeholder="E.g 2"
        value={formData.arms}
      ></TextInput>
      <TextInput
        name="recruitment_days"
        handleChange={handleChange}
        placeholder="E.g 5"
        value={formData.recruitment_days}
      ></TextInput>
      <TextInput
        name="offset_days"
        handleChange={handleChange}
        placeholder="E.g 3"
        value={formData.offset_days}
      ></TextInput>
    </>
  );
};

export default PipelineExperiment;
