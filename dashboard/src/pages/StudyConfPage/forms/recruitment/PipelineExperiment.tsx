import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useForm, SubmitHandler, UseFormRegister, Path } from 'react-hook-form';
import PrimaryButton from '../../../../components/PrimaryButton';
import { createLabelFor } from '../../../../helpers/strings';
import { validate } from '../../../../helpers/objects';
import useCreateStudyConf from '../../../../hooks/useCreateStudyConf';

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
  register: UseFormRegister<FormData>;
  errors?: any;
}

const TextInput: React.FC<TextProps> = ({
  name,
  type,
  valueAsNumber,
  register,
  autoComplete,
  placeholder,
  errors,
}) => (
  <div className="sm:my-4">
    <label className="my-2 block text-sm font-medium text-gray-700">
      {createLabelFor(name)}
    </label>
    <input
      required
      type={type}
      autoComplete={autoComplete}
      placeholder={placeholder}
      {...register(name, {
        valueAsNumber,
      })}
      className="block w-4/5 shadow-sm sm:text-sm rounded-md"
    />
  </div>
);

interface Props {
  id: string;
  data: FormData;
}

const PipelineExperiment: React.FC<Props> = ({ id, data }: Props) => {
  const initialValues = {
    end_date: '',
    start_date: '',
    arms: 0,
    recruitment_days: 0,
    offset_days: 0,
    ad_campaign_name_base: '',
    budget_per_arm: 0,
    max_sample_per_arm: 0,
  };

  const [formData, setFormData] = useState(initialValues);

  const { register, reset, handleSubmit } = useForm<FormData>({
    defaultValues: formData,
  });

  const isMatch = validate(data, initialValues);

  useEffect(() => {
    if (isMatch) {
      setFormData(data);
      reset(data);
    }
  }, [data, isMatch, reset]);

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
    <form onSubmit={handleSubmit(onSubmit)}>
      <TextInput
        name="ad_campaign_name_base"
        type="text"
        register={register}
        autoComplete="on"
        placeholder="E.g vlab-vaping-pilot-2"
      />
      <TextInput
        name="budget_per_arm"
        type="text"
        valueAsNumber={true}
        register={register}
        autoComplete="on"
        placeholder="E.g 8400"
      />
      <TextInput
        name="max_sample_per_arm"
        type="number"
        valueAsNumber={true}
        register={register}
        autoComplete="on"
        placeholder="E.g 1000"
      />
      <TextInput
        name="start_date"
        type="text"
        register={register}
        autoComplete="on"
        placeholder="E.g 2022-07-26T00:00:00"
      />
      <TextInput
        name="end_date"
        type="text"
        register={register}
        autoComplete="on"
        placeholder="E.g 2022-07-26T00:00:00"
      />
      <TextInput
        name="arms"
        type="number"
        valueAsNumber={true}
        register={register}
        autoComplete="on"
        placeholder="E.g 2"
      ></TextInput>
      <TextInput
        name="recruitment_days"
        type="number"
        valueAsNumber={true}
        register={register}
        autoComplete="on"
        placeholder="E.g 2"
      ></TextInput>
      <TextInput
        name="offset_days"
        type="number"
        valueAsNumber={true}
        register={register}
        autoComplete="on"
        placeholder="E.g 2"
      ></TextInput>
      <div className="p-6 text-right">
        <PrimaryButton
          type="submit"
          testId="form-submit-button"
          loading={isLoadingOnCreateStudyConf}
        >
          Save
        </PrimaryButton>
      </div>
    </form>
  );
};

export default PipelineExperiment;
