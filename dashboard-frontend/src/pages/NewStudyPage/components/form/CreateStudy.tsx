import { useForm, SubmitHandler, UseFormRegister, Path } from 'react-hook-form';
import { classNames, createLabelFor } from '../../../../helpers/strings';
import PrimaryButton from '../../../../components/PrimaryButton';
import useCreateStudy from '../../useCreateStudy';

interface IFormValues {
  name: string;
}

type InputProps = {
  label: Path<IFormValues>;
  register: UseFormRegister<IFormValues>;
  required: boolean;
};

const Input = ({ label, register, required }: InputProps) => (
  <div className="sm:my-4">
    <label className="my-2 block text-sm font-medium text-gray-700">
      {createLabelFor(label)}
    </label>
    <input
      {...register(label, { required })}
      className={classNames(
        'p-2.5 block w-4/5 shadow-sm sm:text-sm rounded-md'
      )}
    />
  </div>
);

const CreateStudy = () => {
  const { register, handleSubmit } = useForm<IFormValues>();
  const { createStudy } = useCreateStudy();

  const onSubmit: SubmitHandler<IFormValues> = data => {
    createStudy(data);
  };

  return (
    <div className="md:grid md:grid-cols-3 md:gap-6">
      <div className="md:col-span-1">
        <div className="px-4 sm:px-0"></div>
      </div>
      <div className="mt-5 md:mt-0 md:col-span-2">
        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="px-4 py-3 bg-gray-50 sm:px-6">
            <Input label="name" register={register} required />
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

export default CreateStudy;
