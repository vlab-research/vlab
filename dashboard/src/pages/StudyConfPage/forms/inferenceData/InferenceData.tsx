import React, { useState } from 'react';
import { useParams } from 'react-router-dom';

import SubmitButton from '../../components/SubmitButton';
import useCreateStudyConf from '../../hooks/useCreateStudyConf';
import {
  CreateStudy as StudyType,
  InferenceData as InferenceDataType,
  SourceExtraction as SourceExtractionType,
  GlobalFormData,
} from '../../../../types/conf';
import { getFinishQuestionRef } from '../strata/strata';
import ConfWrapper from '../../components/ConfWrapper';
import ErrorPlaceholder from '../../../../components/ErrorPlaceholder';
import SourceExtraction from './SourceExtraction';

interface Props {
  id: string;
  study: StudyType;
  localData: InferenceDataType | undefined;
  globalData: GlobalFormData;
}

const InferenceData: React.FC<Props> = ({
  id,
  localData,
  globalData,
}: Props) => {


  const dataSourceState = globalData.data_sources?.map(ds => [ds.name, {
    extraction_confs: [{
      name: '',
      location: '',
      key: '',
      functions: [],
      aggregate: '',
      value_type: ''
    }]
  }])
  const initialState = { data_sources: Object.fromEntries(dataSourceState) };

  // Clean out local data with existing sources
  if (localData) {
    for (const key of Object.keys(localData.data_sources)) {
      if (!globalData.data_sources.map(ds => ds.name).includes(key)) {
        delete localData.data_sources[key]
      }
    }
  }

  const [formData, setFormData] = useState<InferenceDataType>(

    // handles edge case where all sources are remove
    localData && Object.keys(localData?.data_sources).length !== 0 ? localData : initialState
  );

  const updateFormData = (source: string, a: SourceExtractionType): void => {
    setFormData({ data_sources: { ...formData.data_sources, [source]: a } });
  };

  const params = useParams<{ studySlug: string }>();
  const studySlug = params.studySlug;
  const { createStudyConf, isLoadingOnCreateStudyConf } = useCreateStudyConf(
    'Infefrence data saved',
    studySlug,
    'inference-data'
  );

  const onSubmit = (e: any): void => {
    e.preventDefault();
    createStudyConf({ data: formData, studySlug, confType: id });
  };

  const dat = Object.entries(formData.data_sources).map(([source, sourceExtraction]) => {
    return { source: source, sourceExtraction }
  })

  const finishQuestionRef = getFinishQuestionRef(globalData.strata);
  const variables = globalData.variables.map(v => v.name);
  const nameOptions = [finishQuestionRef, ...variables];

  return (
    <ConfWrapper>
      <form onSubmit={onSubmit}>
        {dat.map(({ source, sourceExtraction }, index) => {
          const dataSource = globalData.data_sources.find(s => s.name === source)!
          return (
            <SourceExtraction
              key={index}
              source={source}
              dataSource={dataSource}
              nameOptions={nameOptions}
              data={sourceExtraction}
              setData={updateFormData} />
          )
        })}
        <SubmitButton isLoading={isLoadingOnCreateStudyConf} />
      </form>
    </ConfWrapper>
  );
};

const InferenceDataWrapper: React.FC<Props> = props => {
  const { globalData } = props;

  if (!globalData.data_sources) {
    return (
      <ConfWrapper>
        <ErrorPlaceholder
          showImage={true}
          message='Oops! You first need to select some Data Sources before this will work'
          onClickTryAgain={() => window.location.reload()}
        />
      </ConfWrapper>
    )
  }

  return (
    <InferenceData {...props} />
  )
}

export default InferenceDataWrapper;
