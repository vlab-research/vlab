import { useEffect, useState } from 'react';
import { FieldState } from '../../../../types/form';
import { createNameFor } from '../../../../helpers/strings';
import useCreateStudy from '../../../../hooks/useCreateStudy';
import Fieldset from './Fieldset';
import PrimaryButton from '../../../../components/PrimaryButton';
import useCreateStudyConf from '../../../../hooks/useCreateStudyConf';
import { useParams } from 'react-router-dom';
import { StudyConfResource } from '../../../../types/study';

export const Form = (props: any) => {
  const { conf, controller, data } = props;
  const fetchedConfData = data?.data;
  const params = useParams<{ studySlug: string }>();
  const title = createNameFor(conf.title);
  const isCreateStudyForm = title === 'create_a_study';

  const { createStudy, errorOnCreateStudy, isLoadingOnCreateStudy } =
    useCreateStudy();

  const {
    createStudyConf,
    errorOnCreateStudyConf,
    isLoadingOnCreateStudyConf,
  } = useCreateStudyConf();


  const [globalFormData, setFormGlobalFormData] = useState<
    StudyConfResource | any
  >({
    fetchedConfData,
  });

  const localFormData = fetchedConfData && fetchedConfData[title];


  const handleChange = (formData: any) => {

    const updateFormData = (x: any) => {
      setFormGlobalFormData({ ...formData, [title]: x });
    };

    updateFormData(formData);
  };

  const handleSubmit = (e: any) => {
    e.preventDefault();

    const data = {
      [title]: globalFormData[title],
    };

    const slug = params.studySlug;

    isCreateStudyForm
      ? createStudy(globalFormData[title])
      : createStudyConf({ data, slug });
  };

  const errorMessage = isCreateStudyForm
    ? errorOnCreateStudy
    : errorOnCreateStudyConf;

  const isLoading = isCreateStudyForm
    ? isLoadingOnCreateStudy
    : isLoadingOnCreateStudyConf;



  return (
    <div className="md:grid md:grid-cols-3 md:gap-6">
      <div className="md:col-span-1">
        <div className="px-4 sm:px-0"></div>
      </div>
      <div className="mt-5 md:mt-0 md:col-span-2">
        <form onSubmit={handleSubmit}>
          {(
            <div className="px-4 py-3 bg-gray-50 sm:px-6">
              <Fieldset
                controller={controller}
                conf={conf}
                localFormData={localFormData}
                handleChange={handleChange}
                error_message={errorMessage}
              />
              <div className="p-6 text-right">
                <PrimaryButton
                  type="submit"
                  loading={isLoading}
                  testId="form-submit-button"
                >
                  Create
                </PrimaryButton>
              </div>
            </div>
          )}
        </form>
      </div>
    </div>
  );
};

export default Form;
