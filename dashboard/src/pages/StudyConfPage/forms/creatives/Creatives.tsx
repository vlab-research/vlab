import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import PrimaryButton from '../../../../components/PrimaryButton';
import AddButton from '../../../../components/AddButton';
import DeleteButton from '../../../../components/DeleteButton';
import useCreateStudyConf from '../../hooks/useCreateStudyConf';
import Creative from './Creative';
import {
  Creatives as CreativesType,
  GlobalFormData,
} from '../../../../types/conf';
import { Creative as CreativeType } from '../../../../types/conf';

interface Props {
  id: string;
  localData: CreativesType;
  globalData: GlobalFormData;
  confKeys: string[];
}

const Creatives: React.FC<Props> = ({
  id,
  localData,
  globalData,
  confKeys,
}: Props) => {
  const initialState = [
    {
      name: '',
      body: '',
      button_text: '',
      destination: '',
      image_hash: '',
      link_text: '',
      welcome_message: '',
      tags: null,
    },
  ];

  const [formData, setFormData] = useState<CreativeType[]>(
    localData ? localData : initialState
  );

  const updateFormData = (c: CreativeType, index: number): void => {
    const clone = [...formData];
    clone[index] = c;
    setFormData(clone);
  };

  const params = useParams<{ studySlug: string }>();

  const studySlug = params.studySlug;

  const { createStudyConf, isLoadingOnCreateStudyConf } = useCreateStudyConf(
    'Creatives saved',
    studySlug,
    confKeys,
    'creatives'
  );

  const onSubmit = (e: any): void => {
    e.preventDefault();

    const data = {
      [id]: formData,
    };

    createStudyConf({ data, studySlug });
  };

  const addCreative = (): void => {
    setFormData([...formData, ...initialState]);
  };

  const deleteCreative = (i: number): void => {
    const newArr = formData.filter((_: CreativeType, ii: number) => ii !== i);

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
                    <ul>
                      <Creative
                        key={index}
                        data={d}
                        index={index}
                        destinations={
                          globalData.destinations && globalData.destinations
                        }
                        updateFormData={updateFormData}
                        studySlug={studySlug}
                      />
                      {formData.length > 1 && (
                        <div key={`${d.name}-${index}`}>
                          <div className="flex flex-row w-4/5 justify-between items-center">
                            <div className="flex w-full h-0.5 mr-4 rounded-md bg-gray-400"></div>
                            <DeleteButton
                              onClick={() => deleteCreative(index)}
                            ></DeleteButton>
                          </div>
                          <div />
                        </div>
                      )}
                    </ul>
                  );
                })}
                <AddButton onClick={addCreative} label="Add a new creative" />
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

export default Creatives;
