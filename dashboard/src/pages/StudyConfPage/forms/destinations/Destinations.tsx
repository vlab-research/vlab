import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import PrimaryButton from '../../../../components/PrimaryButton';
import AddButton from '../../../../components/AddButton';
import DeleteButton from '../../../../components/DeleteButton';
import useCreateStudyConf from '../../hooks/useCreateStudyConf';
import Destination from './Destination';
import { Destinations as DestinationTypes } from '../../../../types/conf';
import { Destination as DestinationType } from '../../../../types/conf';
import ConfWrapper from '../../components/ConfWrapper';
interface Props {
  id: string;
  localData: DestinationTypes;
  confKeys: string[];
}

const Destinations: React.FC<Props> = ({ id, localData, confKeys }: Props) => {
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

  const params = useParams<{ studySlug: string }>();

  const studySlug = params.studySlug;

  const { createStudyConf, isLoadingOnCreateStudyConf } = useCreateStudyConf(
    'Destinations saved',
    studySlug,
    confKeys,
    'destinations'
  );

  const onSubmit = (e: any): void => {
    e.preventDefault();

    const data = {
      [id]: formData,
    };

    createStudyConf({ data, studySlug });
  };

  const addDestination = (): void => {
    setFormData([...formData, ...initialState]);
  };

  const deleteDestination = (i: number): void => {
    const newArr = formData.filter(
      (_: DestinationType, ii: number) => ii !== i
    );

    setFormData(newArr);
  };

  return (
    <ConfWrapper>
      <form onSubmit={onSubmit}>
        <div className="mb-8">
          {formData.map((d: DestinationType, index: number) => {
            return (
              <ul key={index}>
                <Destination
                  data={d}
                  type={d.type}
                  index={index}
                  updateFormData={updateFormData}
                />
                {formData.length > 1 && (
                  <div key={`${d.name}-${index}`}>
                    <div className="flex flex-row w-4/5 justify-between items-center">
                      <div className="flex w-full h-0.5 mr-4 rounded-md bg-gray-400"></div>
                      <DeleteButton
                        onClick={() => deleteDestination(index)}
                      ></DeleteButton>
                    </div>
                    <div />
                  </div>
                )}
              </ul>
            );
          })}
          <AddButton onClick={addDestination} label="Add destination" />
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

export default Destinations;
