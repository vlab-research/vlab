import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import Fieldset from './Fieldset';
import PrimaryButton from '../../../../components/PrimaryButton';
import { createNameFor } from '../../../../helpers/strings';
import useCreateStudy from '../../../../hooks/useCreateStudy';
import useCreateStudyConf from '../../../../hooks/useCreateStudyConf';
import { StudyConfResource } from '../../../../types/study';
import { ConfBase } from '../../../../types/conf';

type Props = {
  conf: ConfBase;
  data?: any;
};

const Form: React.FC<Props> = ({ conf, data }) => {
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

  const [globalFormData, setGlobalFormData] = useState<any>({
    fetchedConfData,
  });

  const localFormData = fetchedConfData && fetchedConfData[title];

  const handleChange = (formData: any) => {
    const updateFormData = (x: any) => {
      setGlobalFormData(x);
    };

    updateFormData(formData);
  };

  const handleSubmit = (e: any) => {
    e.preventDefault();

    const data: StudyConfResource = {
      [title]: globalFormData,
    };

    const slug = params.studySlug;

    isCreateStudyForm
      ? createStudy(globalFormData[title])
      : createStudyConf({ data, slug });
  };

  const error = isCreateStudyForm ? errorOnCreateStudy : errorOnCreateStudyConf;

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
          {
            <div className="px-4 py-3 bg-gray-50 sm:px-6">
              <Fieldset
                conf={conf}
                localFormData={localFormData}
                handleChange={handleChange}
                error={error}
              ></Fieldset>
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
          }
        </form>
      </div>
    </div>
  );
};

export default Form;
