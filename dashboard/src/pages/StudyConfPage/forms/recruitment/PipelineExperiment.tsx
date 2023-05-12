import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useForm, SubmitHandler, UseFormRegister, Path } from 'react-hook-form';
import PrimaryButton from '../../../../components/PrimaryButton';
import { classNames, createLabelFor } from '../../../../helpers/strings';
import useCreateStudyConf from '../../../../hooks/useCreateStudyConf';
import { clearCacheWhileRefetching } from '../../../../hooks/useStudyConf';

export interface FormData {
  ad_campaign_name_base: string;
  budget_per_arm: number;
  max_sample_per_arm: number;
  start_date: string;
  end_date: string;
  arms: number;
  recruitment_days: number;
  offset_days: number;
}

interface TextProps {
  name: Path<FormData>;
  type?: string;
  valueAsNumber?: boolean;
  autoComplete: string;
  placeholder: string;
  required: boolean;
  register: UseFormRegister<FormData>;
  errors?: any;
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

interface Props {
  id: string;
  data: FormData;
}

const PipelineExperiment: React.FC<Props> = ({ id, data }: Props) => {
  const initialValues = {};

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

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <TextInput
        name="ad_campaign_name_base"
        type="text"
        register={register}
        required
        autoComplete="on"
        placeholder="E.g vlab-vaping-pilot-2"
        errors={errors['ad_campaign_name_base']}
      />
      <TextInput
        name="budget_per_arm"
        type="text"
        valueAsNumber={true}
        register={register}
        required
        autoComplete="on"
        placeholder="E.g 8400"
        errors={errors['budget_per_arm']}
      />
      <TextInput
        name="max_sample_per_arm"
        type="text"
        valueAsNumber={true}
        register={register}
        required
        autoComplete="on"
        placeholder="E.g 1000"
        errors={errors['max_sample_per_arm']}
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
      <TextInput
        name="arms"
        type="text"
        valueAsNumber={true}
        register={register}
        required
        autoComplete="on"
        placeholder="E.g 2"
        errors={errors['arms']}
      ></TextInput>
      <TextInput
        name="recruitment_days"
        type="text"
        valueAsNumber={true}
        register={register}
        required
        autoComplete="on"
        placeholder="E.g 2"
        errors={errors['recruitment_days']}
      ></TextInput>
      <TextInput
        name="offset_days"
        type="text"
        valueAsNumber={true}
        register={register}
        required
        autoComplete="on"
        placeholder="E.g 2"
        errors={errors['offset_days']}
      ></TextInput>
      <div className="p-6 text-right">
        <PrimaryButton type="submit" testId="form-submit-button">
          Create
        </PrimaryButton>
      </div>
    </form>
  );
};

export default PipelineExperiment;
