import { useForm, SubmitHandler, UseFormRegister, Path } from 'react-hook-form';
import PrimaryButton from '../../../components/PrimaryButton';
import { classNames } from '../../../helpers/strings';
import useCreateStudy from '../../../hooks/useCreateStudy';

interface FormData {
  name: string;
}

type TextProps = {
  name: Path<FormData>;
  label: string;
  register: UseFormRegister<FormData>;
  required: boolean;
  autoComplete: string;
  placeholder: string;
};

const TextInput = ({
  name,
  label,
  required,
  autoComplete,
  placeholder,
  register,
}: TextProps) => (
  <div className="sm:my-4">
    <label className="my-2 block text-sm font-medium text-gray-700">
      {label}
    </label>
    <input
      autoComplete={autoComplete}
      placeholder={placeholder}
      {...register(name, { required })}
      className={classNames(
        'p-2.5 block w-4/5 shadow-sm sm:text-sm rounded-md'
      )}
    />
  </div>
);

const CreateStudy: React.FC<any> = () => {
  const { register, handleSubmit } = useForm({
    defaultValues: {
      name: '',
    },
  });

  const { createStudy } = useCreateStudy();

  const onSubmit: SubmitHandler<FormData> = data => createStudy(data);

  return (
    <div className="md:grid md:grid-cols-3 md:gap-6">
      <div className="md:col-span-1">
        <div className="px-4 sm:px-0"></div>
      </div>
      <div className="mt-5 md:mt-0 md:col-span-2">
        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="px-4 py-3 bg-gray-50 sm:px-6">
            <TextInput
              name={'name'}
              label={'Give your study a name'}
              required
              autoComplete="on"
              placeholder="E.g example-fly-conf"
              register={register}
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

export default CreateStudy;
