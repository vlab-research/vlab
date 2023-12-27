import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import DataSource from './DataSource';
import SubmitButton from '../../components/SubmitButton';
import AddButton from '../../../../components/AddButton';
import DeleteButton from '../../../../components/DeleteButton';
import useCreateStudyConf from '../../hooks/useCreateStudyConf';
import {
  CreateStudy as StudyType,
  DataSource as DataSourceType,
} from '../../../../types/conf';
import ConfWrapper from '../../components/ConfWrapper';
import useAccounts from '../../../AccountsPage/hooks/useAccounts';

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
    },
  ];

  const [formData, setFormData] = useState<DataSourceType[]>(
    localData ? localData : initialState
  );

  const updateFormData = (a: DataSourceType, index: number): void => {
    const clone = [...formData];
    clone[index] = a;
    setFormData(clone);
  };

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

  const addItem = (): void => {
    setFormData([...formData, ...initialState]);
  };

  const deleteItem = (i: number): void => {
    const newArr = formData.filter((_, ii) => ii !== i);
    setFormData(newArr);
  };

  return (
    <ConfWrapper>
      <form onSubmit={onSubmit}>
        <div className="mb-8">
          {formData.map((d, index) => {
            return (
              <ul key={index}>
                <DataSource
                  accounts={accounts}
                  data={d}
                  index={index}
                  updateFormData={updateFormData}
                />
                {formData.length > 1 && (
                  <div key={`${d.name}-${index}`}>
                    <div className="flex flex-row w-4/5 justify-between items-center">
                      <div className="flex w-full h-0.5 mr-4 rounded-md bg-gray-400"></div>
                      <DeleteButton
                        onClick={() => deleteItem(index)}
                      ></DeleteButton>
                    </div>
                    <div />
                  </div>
                )}
              </ul>
            );
          })}
          <AddButton onClick={addItem} label="Add data source" />
        </div>

        <SubmitButton isLoading={isLoadingOnCreateStudyConf} />
      </form>
    </ConfWrapper>
  );
};

export default DataSources;
