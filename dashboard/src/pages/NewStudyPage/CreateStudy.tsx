import { useState } from 'react';
import PrimaryButton from '../../components/PrimaryButton';
import useCreateStudy from './hooks/useCreateStudy';
import {
  GenericTextInput,
  TextInputI,
} from '../StudyConfPage/components/TextInput';

interface FormData {
  name: string;
}

const TextInput = GenericTextInput as TextInputI<FormData>;

const CreateStudy: React.FC<any> = () => {
  const initialState = { name: '' };

  const [formData, setFormData] = useState<FormData>(initialState);

  const updateFormData = (d: FormData): void => {
    setFormData(d);
  };

  const { createStudy, isLoadingOnCreateStudy } = useCreateStudy(formData.name);

  const onSubmit = (e: any): void => {
    e.preventDefault();

    createStudy(formData);
  };

  const handleChange = (e: any) => {
    const { name, value } = e.target;

    updateFormData({ ...formData, [name]: value });
  };

  return (
    <div className="md:grid md:grid-cols-3 md:gap-6">
      <div className="md:col-span-1">
        <div className="px-4 sm:px-0"></div>
      </div>
      <div className="mt-5 md:mt-0 md:col-span-2">
        <form onSubmit={onSubmit}>
          <div className="px-4 py-3 bg-gray-50 sm:px-6">
            <TextInput
              name="name"
              handleChange={handleChange}
              placeholder="E.g example-fly"
              value={formData.name}
            />
            <div className="p-6 text-right">
              <PrimaryButton
                leftIcon="PencilAltIcon"
                type="submit"
                testId="form-submit-button"
                loading={isLoadingOnCreateStudy}
              >
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
