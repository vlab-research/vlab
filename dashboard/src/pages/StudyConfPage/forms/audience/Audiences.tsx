import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import Audience from './Audience';
import PrimaryButton from '../../../../components/PrimaryButton';
import AddButton from '../../../../components/AddButton';
import DeleteButton from '../../../../components/DeleteButton';
import useCreateStudyConf from '../../../../hooks/useCreateStudyConf';
import { Audiences as AudiencesType } from '../../../../types/conf';
import { Audience as AudienceType } from '../../../../types/conf';

interface Props {
  id: string;
  localData: AudiencesType;
}

const Audiences: React.FC<Props> = ({ id, localData }: Props) => {
  const initialState = [
    {
      name: '',
      subtype: '',
    },
  ];

  const [formData, setFormData] = useState<AudiencesType>(
    localData ? localData : initialState
  );

  const updateFormData = (d: AudienceType, index: number): void => {
    const clone = [...formData];
    clone[index] = d;
    setFormData(clone);
  };

  const { createStudyConf, isLoadingOnCreateStudyConf } = useCreateStudyConf(
    true,
    'Study settings saved'
  );
  const {
    createStudyConf: deleteStudyConf,
    isLoadingOnCreateStudyConf: isDeleting,
  } = useCreateStudyConf(false, 'Audience deleted');

  const params = useParams<{ studySlug: string }>();

  const onSubmit = (e: any): void => {
    e.preventDefault();

    const studySlug = params.studySlug;

    const data = {
      [id]: formData,
    };

    createStudyConf({ data, studySlug });
  };

  const addAudience = (): void => {
    setFormData([...formData, ...initialState]);
  };

  const deleteAudience = (index: number): void => {
    const newArr = formData.filter((d: AudienceType, i: number) => index !== i);

    const data = {
      [id]: newArr,
    };

    const studySlug = params.studySlug;

    deleteStudyConf({ data, studySlug });

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
                <ul>
                  {formData.map((d: AudienceType, index: number) => {
                    return (
                      <li>
                        <Audience
                          key={index}
                          data={d}
                          index={index}
                          updateFormData={updateFormData}
                        />
                        {formData.length > 1 && (
                          <div key={`${d.name}-${index}`}>
                            <div className="flex flex-row w-4/5 justify-between items-center mb-4">
                              <div className="w-full h-0.5 mr-8 rounded-md bg-gray-400"></div>
                              <DeleteButton
                                loading={isDeleting}
                                onClick={() => deleteAudience(index)}
                              ></DeleteButton>
                            </div>
                            <div />
                          </div>
                        )}
                      </li>
                    );
                  })}
                  <AddButton onClick={addAudience} />
                  <span className="ml-4 italic text-gray-700 text-sm">
                    Add a new audience
                  </span>
                </ul>
              </div>

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
          </div>
        </div>
      </div>
    </div>
  );
};

export default Audiences;