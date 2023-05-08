import useCreateStudyConf from '../../../hooks/useCreateStudyConf';
import { useParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import useStudyConf from '../../../hooks/useStudyConf';

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

const Test = () => {
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm();

  const { createStudyConf } = useCreateStudyConf();
  const params = useParams<{ studySlug: string }>();
  const id = 'general';

  const onSubmit = (formData: any) => {
    const slug = params.studySlug;

    const data = {
      [id]: formData,
    };

    console.log(data);

    createStudyConf({ data, slug });
  };

  console.log(watch('page_id'));

  const studyConf = useStudyConf(params.studySlug);

  const data = studyConf.data && studyConf.data[id];

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input defaultValue={data ? data.page_id : ''} {...register('page_id')} />
      <input {...register('instagram_id', { required: true })} />
      {errors.exampleRequired && <span>This field is required</span>}
      <input type="submit" />
    </form>
  );
};

export default Test;
