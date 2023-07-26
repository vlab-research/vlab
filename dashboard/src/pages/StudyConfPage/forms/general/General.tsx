import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useForm, UseFormRegister, Path } from 'react-hook-form';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import PrimaryButton from '../../../../components/PrimaryButton';
import objectives from '../../../../fixtures/general/objectives';
import destinations from '../../../../fixtures/general/destinations';
import optimizationGoals from '../../../../fixtures/general/optimizationGoals';
import { createLabelFor } from '../../../../helpers/strings';
import { getFirstOption } from '../../../../helpers/arrays';
import useCreateStudyConf from '../../hooks/useCreateStudyConf';
import { General as FormData } from '../../../../types/conf';

const TextInput = GenericTextInput as TextInputI<FormData>;

interface Props {
  id: string;
  localData: FormData;
  confKeys: string[];
}

interface SelectProps {
  name: Path<FormData>;
  options: { name: string; label: string }[];
  register: UseFormRegister<FormData>;
}

const Select: React.FC<SelectProps> = ({
  name,
  options,
  register,
}: SelectProps) => (
  <div className="sm:my-4">
    <label className="my-2 block text-sm font-medium text-gray-700">
      {createLabelFor(name)}
    </label>
    <select
      {...register(name)}
      className="w-4/5 mt-1 block shadow-sm sm:text-sm rounded-md"
    >
      {options.map((option: { name: string; label: string }, i: number) => (
        <option key={i} value={option.name.toUpperCase()}>
          {option.label}
        </option>
      ))}
    </select>
  </div>
);

const General: React.FC<Props> = ({ id, localData, confKeys }: Props) => {
  const initialState = {
    objective: getFirstOption(objectives).toUpperCase(),
    optimization_goal: getFirstOption(optimizationGoals).toUpperCase(),
    destination_type: getFirstOption(destinations).toUpperCase(),
    page_id: '',
    min_budget: 0,
    opt_window: 0,
    instagram_id: '',
    ad_account: '',
  };

  const { register } = useForm<FormData>({});

  const [formData, setFormData] = useState<FormData>(initialState);

  useEffect(() => {
    localData && setFormData(localData);
  }, [localData]);

  const updateFormData = (d: FormData): void => {
    setFormData(d);
  };

  const params = useParams<{ studySlug: string }>();

  const studySlug = params.studySlug;

  const { createStudyConf, isLoadingOnCreateStudyConf } = useCreateStudyConf(
    'General settings saved',
    studySlug,
    confKeys,
    'general'
  );

  const onSubmit = (e: any): void => {
    e.preventDefault();

    const data = {
      [id]: formData,
    };

    createStudyConf({ data, studySlug });
  };

  const validateInput = (name: string, value: any) => {
    if (name === 'min_budget') {
      if (!value) {
        return parseFloat('0');
      }
      return parseFloat(value);
    }
    if (name === 'opt_window') {
      if (!value) {
        return parseInt('0');
      }
      return parseInt(value);
    }
    return value;
  };

  const handleChange = (e: any) => {
    const { name, value } = e.target;

    updateFormData({ ...formData, [name]: validateInput(name, value) });
  };

  return (
    <div className="md:grid md:grid-cols-3 md:gap-6">
      <div className="md:col-span-1">
        <div className="px-4 sm:px-0"></div>
      </div>
      <div className="mt-5 md:mt-0 md:col-span-2">
        <form onSubmit={onSubmit}>
          <div className="px-4 py-3 bg-gray-50 sm:px-6">
            <Select
              name="objective"
              options={objectives}
              register={register}
            ></Select>
            <Select
              name="optimization_goal"
              options={optimizationGoals}
              register={register}
            ></Select>
            <Select
              name="destination_type"
              options={destinations}
              register={register}
            ></Select>
            <TextInput
              name="page_id"
              handleChange={handleChange}
              placeholder="E.g 1855355231229529"
              value={formData.page_id}
            />
            <TextInput
              name="min_budget"
              handleChange={handleChange}
              placeholder="E.g 8400"
              value={formData.min_budget}
            />
            <TextInput
              name="opt_window"
              handleChange={handleChange}
              placeholder="E.g 48"
              value={formData.opt_window}
            />
            <TextInput
              name="instagram_id"
              handleChange={handleChange}
              required={false}
              placeholder="E.g 2327764173962588"
              value={formData.instagram_id}
            />
            <TextInput
              name="ad_account"
              handleChange={handleChange}
              placeholder="E.g 1342820622846299"
              value={formData.ad_account}
            />
            <div className="p-6 text-right">
              <PrimaryButton
                leftIcon="CheckCircleIcon"
                type="submit"
                testId="form-submit-button"
                loading={isLoadingOnCreateStudyConf}
              >
                Next
              </PrimaryButton>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default General;
