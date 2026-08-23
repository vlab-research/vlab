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
import { initialExtractionConfs } from './generateLookupConfs';

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


  // A source with nothing saved starts from the study's declared variables
  // rather than from a blank row: a stratified ad study attributes its
  // respondents, and the researcher already named the variables. Purely a
  // default — anything saved is loaded in preference to it, below.
  const variableNames = globalData.variables.map(v => v.name);

  const dataSourceState = globalData.data_sources?.map(ds => [ds.name, {
    extraction_confs: initialExtractionConfs(ds.source, variableNames)
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

  const userVariables = dat.map(({ sourceExtraction }) => sourceExtraction.user_variable).filter(x => !!x) as string[];
  const nameOptions = [finishQuestionRef, ...variableNames, ...userVariables];

  const multipleSources = dat.length > 1;

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
              multipleSources={multipleSources}
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

  if (!globalData.strata) {
    return (
      <ConfWrapper>
        <ErrorPlaceholder
          showImage={true}
          message='Oops! You first need to configure your strata!'
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
