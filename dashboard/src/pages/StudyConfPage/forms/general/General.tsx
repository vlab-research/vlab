import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useForm, SubmitHandler, UseFormRegister, Path } from 'react-hook-form';
import PrimaryButton from '../../../../components/PrimaryButton';
import objectives from '../../../../fixtures/general/objectives';
import destinations from '../../../../fixtures/general/destinations';
import optimizationGoals from '../../../../fixtures/general/optimizationGoals';
import { createLabelFor } from '../../../../helpers/strings';
import { getFirstOption } from '../../../../helpers/arrays';
import useCreateStudyConf from '../../../../hooks/useCreateStudyConf';

interface FormData {
  objective: string;
  optimization_goal: string;
  destination_type: string;
  page_id: string;
  min_budget: number;
  opt_window: number;
  instagram_id?: string | undefined;
  ad_account: string;
}

interface TextProps {
  name: Path<FormData>;
  type?: string;
  valueAsNumber?: boolean;
  autoComplete: string;
  placeholder: string;
  register: UseFormRegister<FormData>;
  required?: boolean;
}

const TextInput: React.FC<TextProps> = ({
  name,
  type,
  valueAsNumber,
  register,
  autoComplete,
  placeholder,
  required = true,
}) => (
  <div className="sm:my-4">
    <label className="my-2 block text-sm font-medium text-gray-700">
      {createLabelFor(name)}
    </label>
    <input
      required={required}
      type={type}
      autoComplete={autoComplete}
      placeholder={placeholder}
      {...register(name, {
        valueAsNumber,
      })}
      className="block w-4/5 shadow-sm sm:text-sm rounded-md"
    />
    {required === false && (
      <span className="m-4 italic text-gray-700 text-xs">Optional</span>
    )}
  </div>
);

interface SelectProps {
  name: Path<FormData>;
  options: SelectOption[];
  register: UseFormRegister<FormData>;
}

interface SelectOption {
  name: string;
  label?: string;
  code?: string;
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
      {options.map((option: SelectOption, i: number) => (
        <option key={i} value={option.name.toUpperCase()}>
          {option.label}
        </option>
      ))}
    </select>
  </div>
);

interface Props {
  id: string;
  localData: FormData;
}

const General: React.FC<Props> = ({ id, localData }: Props) => {
  const initialValues = {
    objective: getFirstOption(objectives).toUpperCase(),
    optimization_goal: getFirstOption(optimizationGoals).toUpperCase(),
    destination_type: getFirstOption(destinations).toUpperCase(),
    page_id: '',
    min_budget: 0,
    opt_window: 0,
    ad_account: '',
  };

  const [formData, setFormData] = useState(initialValues);

  const { register, reset, handleSubmit } = useForm<FormData>({
    defaultValues: formData,
  });

  useEffect(() => {
    setFormData(localData);
    reset(localData);
  }, [localData, reset]);

  const { createStudyConf, isLoadingOnCreateStudyConf } = useCreateStudyConf(
    true,
    'Study settings saved'
  );
  const params = useParams<{ studySlug: string }>();

  const onSubmit: SubmitHandler<FormData> = formData => {
    const studySlug = params.studySlug;

    const data = {
      [id]: formData,
    };

    createStudyConf({ data, studySlug });
  };

  return (
    <div className="md:grid md:grid-cols-3 md:gap-6">
      <div className="md:col-span-1">
        <div className="px-4 sm:px-0"></div>
      </div>
      <div className="mt-5 md:mt-0 md:col-span-2">
        <form onSubmit={handleSubmit(onSubmit)}>
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
              type="text"
              register={register}
              autoComplete="on"
              placeholder="E.g 1855355231229529"
            />
            <TextInput
              name="min_budget"
              type="text"
              valueAsNumber={true}
              register={register}
              autoComplete="on"
              placeholder="E.g 8400"
            />
            <TextInput
              name="opt_window"
              type="text"
              valueAsNumber={true}
              register={register}
              autoComplete="on"
              placeholder="E.g 48"
            />
            <TextInput
              name="instagram_id"
              type="text"
              register={register}
              autoComplete="on"
              placeholder="E.g 2327764173962588"
              required={false}
            />
            <TextInput
              name="ad_account"
              type="text"
              register={register}
              autoComplete="on"
              placeholder="E.g 1342820622846299"
            />
            <div className="p-6 text-right">
              <PrimaryButton
                type="submit"
                testId="form-submit-button"
                loading={isLoadingOnCreateStudyConf}
              >
                Save
              </PrimaryButton>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default General;
