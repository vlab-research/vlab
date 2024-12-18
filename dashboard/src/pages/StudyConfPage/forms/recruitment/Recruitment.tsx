import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import Simple from './Simple';
import Destination from './Destination';
import PipelineExperiment from './PipelineExperiment';
import PrimaryButton from '../../../../components/PrimaryButton';
import { GenericSelect, SelectI } from '../../components/Select';
import recruitmentTypes from '../../../../fixtures/recruitment/types';
import {
  GlobalFormData,
  RecruitmentSimple,
  RecruitmentDestination,
  PipelineExperiment as PipelineExperimentType,
  Recruitment as LocalData
} from '../../../../types/conf';
import useCreateStudyConf from '../../hooks/useCreateStudyConf';
import ConfWrapper from '../../components/ConfWrapper';
const Select = GenericSelect as SelectI<any>;

interface Props {
  id: string;
  globalData: GlobalFormData;
  localData: any;
}

const duckTypeRecruitmentType = (localData: any) => {
  if (localData?.arms) {
    return 'pipeline_experiment'
  } else if (localData?.ad_campaign_name_base) {
    return 'destination'
  } else {
    return 'simple'
  }
}

const Recruitment: React.FC<Props> = ({
  id,
  globalData,
  localData,
}: Props) => {

  const [recruitmentType, setRecruitmentType] = useState<string>(duckTypeRecruitmentType(localData));

  const initialState: any[] = [
    {
      end_date: '2024-01-07T00:00',
      start_date: '2024-01-01T00:00',
      ad_campaign_name: '',
      objective: '',
      optimization_goal: '',
      destination_type: '',
      min_budget: 1,
      budget: '',
      max_sample: '',
      type: 'simple',
      incentive_per_respondent: 0,
    },
    {
      ad_campaign_name_base: '',
      objective: '',
      optimization_goal: '',
      destination_type: '',
      min_budget: 1,
      budget_per_arm: '',
      end_date: '2024-01-07T00:00',
      start_date: '2024-01-01T00:00',
      max_sample_per_arm: '',
      arms: '',
      recruitment_days: '',
      offset_days: '',
      type: 'pipeline_experiment',
      incentive_per_respondent: 0,
    },
    {
      destination: '',
      ad_campaign_name_base: '',
      objective: '',
      optimization_goal: '',
      destination_type: '',
      min_budget: 1,
      budget_per_arm: '',
      end_date: '2024-01-07T00:00',
      start_date: '2024-01-01T00:00',
      max_sample_per_arm: '',
      type: 'destination',
      incentive_per_respondent: 0,
    },
  ];

  const [formData, setFormData] = useState<LocalData>(
    localData ? localData : initialState.find((obj: any) => obj.type === recruitmentType)
  );

  const handleSelectChange = (e: any) => {
    const { value } = e.target;
    setRecruitmentType(value);
    const fields = initialState.find((obj: any) => obj.type === value);
    setFormData(fields);
  };

  const params = useParams<{ studySlug: string }>();

  const studySlug = params.studySlug;

  const { createStudyConf, isLoadingOnCreateStudyConf } = useCreateStudyConf(
    'Recruitment settings saved',
    studySlug,
    'recruitment'
  );


  const formatData = (data: LocalData) => {
    if ("ad_campaign_name" in data) {
      data.ad_campaign_name = data.ad_campaign_name.trim()
    }

    if ("ad_campaign_name_base" in data) {
      data.ad_campaign_name_base = data.ad_campaign_name_base.trim()
    }

    return data;
  };

  const onSubmit = (e: any): void => {
    e.preventDefault();

    createStudyConf({ data: formatData(formData), studySlug, confType: id });
  };

  return (
    <ConfWrapper>
      <form onSubmit={onSubmit}>
        <Select
          name="destination"
          options={recruitmentTypes}
          handleChange={handleSelectChange}
          value={recruitmentType}
          label="Select a recruitment type"
        ></Select>
        {recruitmentType === 'simple' && (
          <Simple formData={formData as RecruitmentSimple} updateFormData={setFormData} />
        )}
        {recruitmentType === 'pipeline_experiment' && (
          <PipelineExperiment
            formData={formData as PipelineExperimentType}
            updateFormData={setFormData}
          />
        )}
        {recruitmentType === 'destination' && (
          <Destination
            formData={formData as RecruitmentDestination}
            updateFormData={setFormData}
            destinations={globalData.destinations}
            studySlug={studySlug}
          />
        )}
        <div className="p-6 text-right">
          <PrimaryButton
            leftIcon="CheckCircleIcon"
            type="submit"
            testId="form-submit-button"
            loading={isLoadingOnCreateStudyConf}
          >
            Next
          </PrimaryButton>
        </div>
      </form>
    </ConfWrapper>
  );
};

export default Recruitment;
