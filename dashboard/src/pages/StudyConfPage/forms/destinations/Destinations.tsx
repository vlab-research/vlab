import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
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

  const initialState = [
    {
      name: '',
      initial_shortcode: '',
      welcome_message: '',
      button_text: '',
      type: '',
      additional_metadata: null,
    },
  ];

  const [formData, setFormData] = useState<DestinationType[]>(
    localData ? localData : initialState
  );

  // A destination form needs to see its siblings: the inline-stratum link is
  // offered only to a study whose fly destinations are all Messenger, so that a
  // multi-channel study cannot end up attributing two different ways.
  const elementProps = { destinations: formData };

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
          elementProps={elementProps}
        />
        <SubmitButton isLoading={isLoadingOnCreateStudyConf} />
      </form>
    </ConfWrapper>
  );
};

export default Destinations;
