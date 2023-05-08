import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useForm, SubmitHandler, UseFormRegister, Path } from 'react-hook-form';
import PrimaryButton from '../../../components/PrimaryButton';
import objectives from '../../../fixtures/general/objectives';
import destinations from '../../../fixtures/general/destinations';
import optimizationGoals from '../../../fixtures/general/optimizationGoals';
import useCreateStudyConf from '../../../hooks/useCreateStudyConf';
import { classNames, createLabelFor } from '../../../helpers/strings';
import { getFirstOption } from '../../../helpers/arrays';

interface FormData {
  objective: string;
  optimization_goal: string;
  destination_type: string;
  page_id: string;
  min_budget: number;
  opt_window: number;
  instagram_id: string;
  ad_account: string;
}

interface TextProps {
  name: Path<FormData>;
  type?: string;
  autoComplete: string;
  placeholder: string;
  required: boolean;
  register: UseFormRegister<FormData>;
  errors?: any;
}

interface SelectProps {
  name: Path<FormData>;
  options: SelectOption[];
  required: boolean;
  register: UseFormRegister<FormData>;
}

interface SelectOption {
  name: string;
  label?: string;
  code?: string;
}

const TextInput: React.FC<TextProps> = ({
  name,
  type,
  register,
  required,
  autoComplete,
  placeholder,
  errors,
}) => (
  <div className="sm:my-4">
    <label className="my-2 block text-sm font-medium text-gray-700">
      {createLabelFor(name)}
    </label>
    <input
      type={type}
      autoComplete={autoComplete}
      placeholder={placeholder}
      {...register(name, { required })}
      className={classNames(
        'block w-4/5 shadow-sm sm:text-sm rounded-md',
        errors
          ? 'focus:ring-red-500 focus:border-red-500 border-red-300 text-red-900 pr-10'
          : 'focus:ring-indigo-500 focus:border-indigo-500 border-gray-300'
      )}
    />
    <div className="sm:my-2">
      {errors && (
        <span className="my-2 block text-sm font-medium text-red-500">
          {`${createLabelFor(name)} is required`}
        </span>
      )}
    </div>
  </div>
);

const Select: React.FC<SelectProps> = ({
  name,
  options,
  register,
  required,
}: SelectProps) => (
  <div className="sm:my-4">
    <label className="my-2 block text-sm font-medium text-gray-700">
      {createLabelFor(name)}
    </label>
    <select
      {...register(name, { required })}
      className="w-4/5 mt-1 block shadow-sm sm:text-sm rounded-md"
    >
      {options.map((option: SelectOption, i: number) => (
        <option key={i} value={option.name}>
          {option.label || option.name}
        </option>
      ))}
    </select>
  </div>
);

interface Props {
  id: string;
  data: FormData;
}

const General: React.FC<Props> = ({ id, data }: Props) => {
  // console.log('data', data);

  const initialValues = {
    objective: getFirstOption(objectives),
    optimization_goal: getFirstOption(optimizationGoals),
    destination_type: getFirstOption(destinations),
    page_id: '',
    min_budget: 0,
    opt_window: 0,
    instagram_id: '',
    ad_account: '',
  };

  const {
    register,
    formState: { errors, isLoading, defaultValues },
    handleSubmit,
  } = useForm<FormData>({
    defaultValues: data ? data : initialValues,
  });

  const { createStudyConf } = useCreateStudyConf();
  const params = useParams<{ studySlug: string }>();

  const onSubmit: SubmitHandler<FormData> = formData => {
    const slug = params.studySlug;

    const data = {
      [id]: formData,
    };

    console.log('data on submit', data, 'default values', defaultValues);

    createStudyConf({ data, slug });
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
              required
            ></Select>
            <Select
              name="optimization_goal"
              options={optimizationGoals}
              register={register}
              required
            ></Select>
            <Select
              name="destination_type"
              options={destinations}
              register={register}
              required
            ></Select>
            <TextInput
              name="page_id"
              type="text"
              register={register}
              required
              autoComplete="on"
              placeholder="E.g 1855355231229529"
              errors={errors['page_id']}
            />
            <TextInput
              name="min_budget"
              type="number"
              register={register}
              required
              autoComplete="on"
              placeholder="E.g 10"
            />
            <TextInput
              name="opt_window"
              type="number"
              register={register}
              required
              autoComplete="on"
              placeholder="E.g 48"
            />
            <TextInput
              name="instagram_id"
              type="text"
              register={register}
              required
              autoComplete="on"
              placeholder="E.g 2327764173962588"
              errors={errors['instagram_id']}
            />
            <TextInput
              name="ad_account"
              type="text"
              register={register}
              required
              autoComplete="on"
              placeholder="E.g 1342820622846299"
              errors={errors['ad_account']}
            />
            <div className="p-6 text-right">
              <PrimaryButton type="submit" testId="form-submit-button">
                Create
              </PrimaryButton>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default General;
