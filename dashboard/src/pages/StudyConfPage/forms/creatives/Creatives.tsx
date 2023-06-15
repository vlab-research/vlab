import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import Creative from './Creative';
import PrimaryButton from '../../../../components/PrimaryButton';
import AddButton from '../../../../components/AddButton';
import DeleteButton from '../../../../components/DeleteButton';
import useCreateStudyConf from '../../../../hooks/useCreateStudyConf';
import { GlobalFormData } from '../../../../types/conf';
import { Creative as CreativeType } from '../../../../types/conf';
import { Creatives as CreativesType } from '../../../../types/conf';
import { getFirstOption } from '../../../../helpers/arrays';

interface Props {
  id: string;
  globalData: GlobalFormData;
  localData: CreativesType;
}

const Creatives: React.FC<Props> = ({ id, globalData, localData }: Props) => {
  const initialState = [
    {
      name: '',
      body: '',
      button_text: '',
      destination: globalData.destinations
        ? getFirstOption(globalData.destinations)
        : 'Create a destination',
      image_hash: '',
      link_text: '',
      welcome_message: '',
      tags: null,
    },
  ];

  const [formData, setFormData] = useState<CreativeType[]>(
    localData ? localData : initialState
  );

  useEffect(() => {
    if (localData) {
      setFormData(localData);
    }
  }, [localData]);

  const updateFormData = (d: CreativeType, index: number): void => {
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
  } = useCreateStudyConf(false, 'Creative deleted');

  const params = useParams<{ studySlug: string }>();

  const onSubmit = (e: any): void => {
    e.preventDefault();

    const studySlug = params.studySlug;

    const data = {
      [id]: formData,
    };

    createStudyConf({ data, studySlug });
  };

  const addDestination = (): void => {
    setFormData([...formData, ...initialState]);
  };

  const deleteCreatives = (index: number): void => {
    const newArr = formData.filter((d: CreativeType, i: number) => index !== i);

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
                {formData.map((d: CreativeType, index: number) => {
                  return (
                    <>
                      <Creative
                        key={index}
                        data={d}
                        index={index}
                        destinations={
                          globalData.destinations && globalData.destinations
                        }
                        updateFormData={updateFormData}
                      />
                      {formData.length > 1 && (
                        <div key={`${d.name}-${index}`}>
                          <div className="flex flex-row w-4/5 justify-between items-center mb-4">
                            <div className="w-full h-0.5 mr-8 rounded-md bg-gray-400"></div>
                            <DeleteButton
                              loading={isDeleting}
                              onClick={() => deleteCreatives(index)}
                            ></DeleteButton>
                          </div>
                          <div />
                        </div>
                      )}
                    </>
                  );
                })}
                <AddButton onClick={addDestination} />
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

export default Creatives;
