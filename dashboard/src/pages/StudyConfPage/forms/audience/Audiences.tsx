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
import ConfWrapper from '../../components/ConfWrapper';

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
    <ConfWrapper>
      <form onSubmit={onSubmit}>
        <div className="mb-8">
          {formData.map((d: AudienceType, index: number) => {
            return (
              <ul key={index}>
                <Audience
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
          <AddButton onClick={addAudience} label="Add audience" />
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
    </ConfWrapper>
  );
};

export default Audiences;
