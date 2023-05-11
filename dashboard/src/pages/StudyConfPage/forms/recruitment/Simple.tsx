import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useForm, SubmitHandler, UseFormRegister, Path } from 'react-hook-form';
import PrimaryButton from '../../../../components/PrimaryButton';
import { classNames, createLabelFor } from '../../../../helpers/strings';
import useCreateStudyConf from '../../../../hooks/useCreateStudyConf';
import { clearCacheWhileRefetching } from '../../../../hooks/useStudyConf';
import recruitmentTypes from '../../../../fixtures/recruitment/types';

interface FormData {
  recruitment_type: string;
  ad_campaign_name: string;
  budget: number;
  max_sample: number;
  start_date: string;
  end_date: string;
}

interface TextProps {
  name: Path<FormData>;
  type?: string;
  valueAsNumber?: boolean;
  valueAsDate?: boolean;
  autoComplete: string;
  placeholder: string;
  required: boolean;
  register: UseFormRegister<FormData>;
  errors?: any;
}

interface SelectProps {
  name: Path<FormData>;
  options: SelectOption[];
  onChange?: any;
  required: boolean;
  register: UseFormRegister<FormData>;
}

interface SelectOption {
  name: string;
  label: string;
}

const TextInput: React.FC<TextProps> = ({
  name,
  type,
  valueAsNumber,
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
      {...register(name, {
        required,
        valueAsNumber,
      })}
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
  onChange,
  register,
  required,
}: SelectProps) => (
  <div className="sm:my-4">
    <label className="my-2 block text-sm font-medium text-gray-700">
      {createLabelFor(name)}
    </label>
    <select
      {...register(name, { required, onChange })}
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
  callback: any;
}

const Simple: React.FC<Props> = ({ id, data, callback }: Props) => {
  const initialValues = {
    ad_campaign_name: '',
    budget: 0,
    max_sample: 0,
  };

  const [formData, setFormData] = useState(initialValues);

  const {
    register,
    reset,
    formState: { errors },
    handleSubmit,
  } = useForm<FormData>({
    defaultValues: formData,
  });

  useEffect(() => {
    setFormData(data);
    reset(data);
  }, [data, reset]);

  const { createStudyConf } = useCreateStudyConf();
  const params = useParams<{ studySlug: string }>();

  const onSubmit: SubmitHandler<FormData> = formData => {
    const slug = params.studySlug;

    const data = {
      [id]: formData,
    };

    createStudyConf({ data, slug });
    clearCacheWhileRefetching();
  };

  const formKeys = ['simple', 'pipeline_experiment', 'destination'];

  const handleChange = (e: any) => {
    const newIndex = formKeys.indexOf(e.target.value);
    callback(newIndex);
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
              name="recruitment_type"
              options={recruitmentTypes}
              onChange={handleChange}
              register={register}
              required
            ></Select>
            <TextInput
              name="ad_campaign_name"
              type="text"
              register={register}
              required
              autoComplete="on"
              placeholder="E.g vlab-vaping-pilot-2"
              errors={errors['ad_campaign_name']}
            />
            <TextInput
              name="budget"
              type="text"
              valueAsNumber={true}
              register={register}
              required
              autoComplete="on"
              placeholder="E.g 8400"
              errors={errors['budget']}
            />
            <TextInput
              name="max_sample"
              type="text"
              valueAsNumber={true}
              register={register}
              required
              autoComplete="on"
              placeholder="E.g 1000"
              errors={errors['max_sample']}
            />
            <TextInput
              name="start_date"
              type="text"
              register={register}
              required
              autoComplete="on"
              placeholder="E.g 2022-07-26T00:00:00"
              errors={errors['start_date']}
            />
            <TextInput
              name="end_date"
              type="text"
              register={register}
              required
              autoComplete="on"
              placeholder="E.g 2022-07-26T00:00:00"
              errors={errors['end_date']}
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

export default Simple;
