import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import PrimaryButton from '../../../../components/PrimaryButton';
import AddButton from '../../../../components/AddButton';
import DeleteButton from '../../../../components/DeleteButton';
import SubmitButton from '../../components/SubmitButton';
import useCreateStudyConf from '../../hooks/useCreateStudyConf';
import Destination from './Destination';
import { Destinations as DestinationTypes } from '../../../../types/conf';
import { Destination as DestinationType } from '../../../../types/conf';
import ConfWrapper from '../../components/ConfWrapper';
import { GenericListFactory } from '../../components/GenericList';

const DestinationList = GenericListFactory<DestinationType>();

interface Props {
  id: string;
  localData: DestinationTypes;
}

const Destinations: React.FC<Props> = ({ id, localData }: Props) => {

  // TODO: add all the initial states ala Recruitment?
  const initialState = [
    {
      name: '',
      initial_shortcode: '',
      welcome_message: '',
      button_text: '',
      type: 'messenger',
    },
  ];

  const [formData, setFormData] = useState<DestinationType[]>(
    localData ? localData : initialState
  );

  const params = useParams<{ studySlug: string }>();

  const studySlug = params.studySlug;

  const { createStudyConf, isLoadingOnCreateStudyConf } = useCreateStudyConf(
    'Destinations saved',
    studySlug,
    'destinations'
  );

  const onSubmit = (e: any): void => {
    e.preventDefault();
    createStudyConf({ data: formData, studySlug, confType: id });
  };

  return (
    <ConfWrapper>
      <form onSubmit={onSubmit}>
        <DestinationList
          Element={Destination}
          data={formData}
          setData={setFormData}
          initialState={initialState}
          elementName="destination"
        />
        <SubmitButton isLoading={isLoadingOnCreateStudyConf} />
      </form>
    </ConfWrapper>
  );
};

export default Destinations;
