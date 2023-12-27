import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import Extraction from './Extraction';
import SubmitButton from '../../components/SubmitButton';
import AddButton from '../../../../components/AddButton';
import DeleteButton from '../../../../components/DeleteButton';
import useCreateStudyConf from '../../hooks/useCreateStudyConf';
import {
  CreateStudy as StudyType,
  InferenceData as InferenceDataType,
} from '../../../../types/conf';
import ConfWrapper from '../../components/ConfWrapper';
import useAccounts from '../../../AccountsPage/hooks/useAccounts';

interface Props {
  id: string;
  study: StudyType;
  localData: InferenceDataType;
}

const InferenceData: React.FC<Props> = ({
  id,
  localData,
}: Props) => {
  const initialState = { data_sources: {} };

  const [formData, setFormData] = useState<InferenceDataType>(
    localData ? localData : initialState
  );

  const updateFormData = (a: InferenceDataType): void => {
    setFormData(a);
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

  // const addItem = (): void => {
  //   setFormData([...formData, ...initialState]);
  // };

  // const deleteItem = (i: number): void => {
  //   const newArr = formData.filter((_, ii) => ii !== i);
  //   setFormData(newArr);
  // };

  const dat = Object.entries(formData.data_sources).map(([source, sourceExtraction]) => {
    return { source: source, sourceExtraction }
  })

  return (
    <ConfWrapper>
      <form onSubmit={onSubmit}>

        {dat.map(({ source, sourceExtraction }, index) => {
          <div>
            <h2> {source}
            </h2>

            {sourceExtraction.extraction_confs.map((e) => {
              <Extraction data={e} updateFormData={updateFormData} index={index} />

            })
            }
          </div>

        })}

        <SubmitButton isLoading={isLoadingOnCreateStudyConf} />
      </form>
    </ConfWrapper>
  );
};

export default InferenceData;
