import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import SubmitButton from '../../components/SubmitButton';
import useCreateStudyConf from '../../hooks/useCreateStudyConf';
import Destination from './Destination';
import { Destinations as DestinationTypes } from '../../../../types/conf';
import { Destination as DestinationType } from '../../../../types/conf';
import ConfWrapper from '../../components/ConfWrapper';
import { GenericListFactory } from '../../components/GenericList';
import { GlobalFormData } from '../../../../types/conf';
import { pageIdForDestination } from './messengerTestLink';

const DestinationList = GenericListFactory<DestinationType>();

interface Props {
  id: string;
  localData: DestinationTypes;
  // Threaded to every tab by Form; used here to resolve each destination's page id
  // from the creatives conf for the Messenger test link.
  globalData?: GlobalFormData;
}

const Destinations: React.FC<Props> = ({ id, localData, globalData }: Props) => {

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

  const creatives = globalData?.creatives;
  const pageIdByName = (creatives || []).reduce<Record<string, string>>((m, c) => {
    const pid = pageIdForDestination([c], c.destination);
    if (c.destination && pid) m[c.destination] = pid;
    return m;
  }, {});
  const fallbackPageId = pageIdForDestination(creatives, undefined);

  return (
    <ConfWrapper>
      <form onSubmit={onSubmit}>
        <DestinationList
          Element={Destination}
          data={formData}
          setData={setFormData}
          initialState={initialState}
          elementName="destination"
          elementProps={{ pageIdByName, fallbackPageId }}
        />
        <SubmitButton isLoading={isLoadingOnCreateStudyConf} />
      </form>
    </ConfWrapper>
  );
};

export default Destinations;
