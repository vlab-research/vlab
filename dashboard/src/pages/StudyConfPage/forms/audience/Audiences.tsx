import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import Audience from './Audience';
import PrimaryButton from '../../../../components/PrimaryButton';
import AddButton from '../../../../components/AddButton';
import DeleteButton from '../../../../components/DeleteButton';
import useCreateStudyConf from '../../hooks/useCreateStudyConf';
import {
  CreateStudy as StudyType,
  Audience as AudienceType,
  Audiences as AudiencesType,
} from '../../../../types/conf';

interface Props {
  id: string;
  study: StudyType;
  localData: AudiencesType;
  confKeys: string[];
}

const Audiences: React.FC<Props> = ({
  id,
  study,
  localData,
  confKeys,
}: Props) => {
  const initialState = [
    {
      name: study.name && `${study.name} respondents`,
      subtype: 'CUSTOM',
    },
  ];

  const [formData, setFormData] = useState<AudiencesType>(
    localData ? localData : initialState
  );

  const updateFormData = (a: AudienceType, index: number): void => {
    const clone = [...formData];
    clone[index] = a;
    setFormData(clone);
  };

  const params = useParams<{ studySlug: string }>();

  const studySlug = params.studySlug;

  const { createStudyConf, isLoadingOnCreateStudyConf } = useCreateStudyConf(
    true,
    'Audiences saved',
    studySlug,
    confKeys,
    'audiences'
  );

  const onSubmit = (e: any): void => {
    e.preventDefault();

    const data = {
      [id]: formData,
    };

    createStudyConf({ data, studySlug });
  };

  const addAudience = (): void => {
    setFormData([...formData, ...initialState]);
  };

  const deleteAudience = (i: number): void => {
    const newArr = formData.filter((_: AudienceType, ii: number) => ii !== i);

    setFormData(newArr);
  };

  return (
    <div className="md:grid md:grid-cols-3 md:gap-6">
      <div className="md:col-span-1">
        <div className="px-4 sm:px-0"></div>
      </div>
      <div className="mt-5 md:mt-0 md:col-span-2">
        <div className="px-4 py-3 bg-gray-50 sm:px-6">
          <div className="sm:my-4">
            <form onSubmit={onSubmit}>
              <div className="mb-8">
                {formData.map((d: AudienceType, index: number) => {
                  return (
                    <ul>
                      <Audience
                        key={index}
                        data={d}
                        index={index}
                        updateFormData={updateFormData}
                      />
                      {formData.length > 1 && (
                        <div key={`${d.name}-${index}`}>
                          <div className="flex flex-row w-4/5 justify-between items-center">
                            <div className="flex w-full h-0.5 mr-4 rounded-md bg-gray-400"></div>
                            <DeleteButton
                              onClick={() => deleteAudience(index)}
                            ></DeleteButton>
                          </div>
                          <div />
                        </div>
                      )}
                    </ul>
                  );
                })}
                <AddButton onClick={addAudience} label="Add a new audience" />
              </div>

              <div className="p-6 text-right">
                <PrimaryButton
                  leftIcon="CheckCircleIcon"
                  type="submit"
                  testId="form-submit-button"
                  loading={isLoadingOnCreateStudyConf}
                >
                  Next
                </PrimaryButton>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Audiences;
