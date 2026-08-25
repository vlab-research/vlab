import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import SubmitButton from '../../components/SubmitButton';
import useCreateStudyConf from '../../hooks/useCreateStudyConf';
import Destination from './Destination';
import { Destinations as DestinationTypes } from '../../../../types/conf';
import { Destination as DestinationType } from '../../../../types/conf';
import ConfWrapper from '../../components/ConfWrapper';
import { GenericListFactory } from '../../components/GenericList';
import { METADATA_MODE } from './refMode';

const DestinationList = GenericListFactory<DestinationType>();

interface Props {
  id: string;
  localData: DestinationTypes;
}

const Destinations: React.FC<Props> = ({ id, localData }: Props) => {

  // A new conf, so it states its mode. See Destination.tsx's emptyStates for
  // why that default lives only in the two constructors.
  const initialState = [
    {
      name: '',
      initial_shortcode: '',
      welcome_message: '',
      button_text: '',
      type: '',
      additional_metadata: null,
      ref_mode: METADATA_MODE,
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
          elementProps={{ savedDestinations: localData }}
        />
        <SubmitButton isLoading={isLoadingOnCreateStudyConf} />
      </form>
    </ConfWrapper>
  );
};

export default Destinations;
