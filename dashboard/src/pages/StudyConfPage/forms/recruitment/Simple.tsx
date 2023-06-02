import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useForm, SubmitHandler, UseFormRegister, Path } from 'react-hook-form';
import PrimaryButton from '../../../../components/PrimaryButton';
import { classNames, createLabelFor } from '../../../../helpers/strings';
import { findMatch } from '../../../../helpers/objects';
import useCreateStudyConf from '../../../../hooks/useCreateStudyConf';

export interface FormData {
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
  register: UseFormRegister<FormData>;
}

const TextInput: React.FC<TextProps> = ({
  name,
  type,
  valueAsNumber,
  register,
  autoComplete,
  placeholder,
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
      className={classNames('block w-4/5 shadow-sm sm:text-sm rounded-md')}
    />
  </div>
);

interface Props {
  id: string;
  data: FormData;
}

const Simple: React.FC<Props> = ({ id, data }: Props) => {
  const initialValues = {
    end_date: '',
    start_date: '',
    ad_campaign_name: '',
    budget: 0,
    max_sample: 0,
  };

  const [formData, setFormData] = useState(initialValues);

  const { register, reset, handleSubmit } = useForm<FormData>({
    defaultValues: formData,
  });

  const isMatch = findMatch(data, initialValues);

  useEffect(() => {
    if (isMatch) {
      setFormData(data);
      reset(data);
    }
  }, [data, isMatch, reset]);

  const { createStudyConf, isLoadingOnCreateStudyConf } = useCreateStudyConf();
  const params = useParams<{ studySlug: string }>();

  const onSubmit: SubmitHandler<FormData> = formData => {
    const slug = params.studySlug;

    const data = {
      [id]: formData,
    };

    createStudyConf({ data, slug });
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <TextInput
        name="ad_campaign_name"
        type="text"
        register={register}
        autoComplete="on"
        placeholder="E.g vlab-vaping-pilot-2"
      />
      <TextInput
        name="budget"
        type="text"
        valueAsNumber={true}
        register={register}
        autoComplete="on"
        placeholder="E.g 8400"
      />
      <TextInput
        name="max_sample"
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
      <div className="p-6 text-right">
        <PrimaryButton
          type="submit"
          testId="form-submit-button"
          loading={isLoadingOnCreateStudyConf}
        >
          Create
        </PrimaryButton>
      </div>
    </form>
  );
};

export default Simple;
