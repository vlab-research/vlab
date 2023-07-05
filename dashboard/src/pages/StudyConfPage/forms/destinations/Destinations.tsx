import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import PrimaryButton from '../../../../components/PrimaryButton';
import AddButton from '../../../../components/AddButton';
import DeleteButton from '../../../../components/DeleteButton';
import useCreateStudyConf from '../../../../hooks/useCreateStudyConf';
import Destination from './Destination';
import { Destinations as DestinationTypes } from '../../../../types/conf';
import { Destination as DestinationType } from '../../../../types/conf';

interface Props {
  id: string;
  localData: DestinationTypes;
}

const Destinations: React.FC<Props> = ({ id, localData }: Props) => {
  const initialState = [
    {
      name: '',
      initial_shortcode: '',
      type: 'messenger',
    },
  ];

  const [formData, setFormData] = useState<DestinationType[]>(
    localData ? localData : initialState
  );

  const updateFormData = (d: DestinationType, index: number): void => {
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
  } = useCreateStudyConf(false, 'Destination deleted');

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

  const deleteDestination = (index: number): void => {
    const newArr = formData.filter(
      (d: DestinationType, i: number) => index !== i
    );

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
                {formData.map((d: DestinationType, index: number) => {
                  return (
                    <>
                      <Destination
                        key={index}
                        data={d}
                        type={d.type}
                        index={index}
                        updateFormData={updateFormData}
                      />
                      {formData.length > 1 && (
                        <div key={`${d.name}-${index}`}>
                          <div className="flex flex-row w-4/5 justify-between items-center mb-4">
                            <div className="w-full h-0.5 mr-8 rounded-md bg-gray-400"></div>
                            <DeleteButton
                              loading={isDeleting}
                              onClick={() => deleteDestination(index)}
                            ></DeleteButton>
                          </div>
                          <div />
                        </div>
                      )}
                    </>
                  );
                })}
                <div className="flex flex-row items-center">
                  <AddButton onClick={addDestination} />
                  <label className="ml-4 italic text-gray-700 text-sm">
                    Add a new destination
                  </label>
                </div>
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

export default Destinations;
