import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import Audience from './Audience';

import { GenericListFactory } from '../../components/GenericList';
import SubmitButton from '../../components/SubmitButton';
import useCreateStudyConf from '../../hooks/useCreateStudyConf';
import {
  CreateStudy as StudyType,
  Audience as AudienceType,
  Audiences as AudiencesType,
} from '../../../../types/conf';
import ConfWrapper from '../../components/ConfWrapper';


const AudienceList = GenericListFactory<AudienceType>();

interface Props {
  id: string;
  study: StudyType;
  localData: AudiencesType;
}


const Audiences: React.FC<Props> = ({
  id,
  study,
  localData,
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

  const params = useParams<{ studySlug: string }>();

  const studySlug = params.studySlug;

  const { createStudyConf, isLoadingOnCreateStudyConf } = useCreateStudyConf(
    'Audiences saved',
    studySlug,
    'audiences'
  );

  const onSubmit = (e: any): void => {
    e.preventDefault();
    createStudyConf({ data: formData, studySlug, confType: id });
  };


  return (
    <ConfWrapper>
      <form onSubmit={onSubmit}>
        <AudienceList
          data={formData}
          setData={setFormData}
          initialState={initialState}
          Element={Audience}
          elementName="audience"
        />
        <SubmitButton isLoading={isLoadingOnCreateStudyConf} />

      </form>
    </ConfWrapper>
  );
};

export default Audiences;
