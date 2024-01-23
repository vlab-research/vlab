import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import DataSource from './DataSource';
import SubmitButton from '../../components/SubmitButton';
import useCreateStudyConf from '../../hooks/useCreateStudyConf';
import {
  CreateStudy as StudyType,
  DataSource as DataSourceType,
} from '../../../../types/conf';
import ConfWrapper from '../../components/ConfWrapper';
import useAccounts from '../../../AccountsPage/hooks/useAccounts';
import { GenericListFactory } from '../../components/GenericList';

const DataSourceList = GenericListFactory<DataSourceType>();

interface Props {
  id: string;
  study: StudyType;
  localData: DataSourceType[];
}


const DataSources: React.FC<Props> = ({
  id,
  localData,
}: Props) => {
  const initialState = [
    {
      name: '',
      source: '',
      credentials_key: '',
      config: { survey_name: '' },
    },
  ];

  const [formData, setFormData] = useState<DataSourceType[]>(
    localData ? localData : initialState
  );

  const params = useParams<{ studySlug: string }>();

  const studySlug = params.studySlug;

  const { createStudyConf, isLoadingOnCreateStudyConf } = useCreateStudyConf(
    'Data sources saved',
    studySlug,
    'data-sources'
  );

  const { query } = useAccounts();
  const accounts = query.data?.filter(a => a.authType !== 'facebook') || [];

  const onSubmit = (e: any): void => {
    e.preventDefault();
    createStudyConf({ data: formData, studySlug, confType: id });
  };


  return (
    <ConfWrapper>
      <form onSubmit={onSubmit}>
        <DataSourceList
          Element={DataSource}
          elementName="data source"
          elementProps={{ accounts: accounts }}
          data={formData}
          setData={setFormData}
          initialState={initialState}
        />
        <SubmitButton isLoading={isLoadingOnCreateStudyConf} />
      </form>
    </ConfWrapper>
  );
};

export default DataSources;
