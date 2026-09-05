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
  Recruitment as LocalData,
} from '../../../../types/conf';
import useCreateStudyConf from '../../hooks/useCreateStudyConf';
import ConfWrapper from '../../components/ConfWrapper';
const Select = GenericSelect as SelectI<any>;

interface Props {
  id: string;
  globalData: GlobalFormData;
  localData: any;
}

// Prefer the stored tag; fall back to shape for confs written before adopt
// started keeping it.
//
// This order is NOT adopt's. `_infer_recruitment_type` (study_conf.py) tests
// type -> ad_campaign_name -> arms -> destinations, and raises when none is
// present; this tests type -> arms -> ad_campaign_name_base -> simple, and
// treats "none of the above" as simple. They agree on every shape this form
// can produce, which is the only set that matters here: each of the three
// initialState objects carries exactly one arm's fields, so `arms` implies no
// `ad_campaign_name` and `ad_campaign_name_base` implies the same. They would
// disagree on a hand-authored body carrying fields from two arms -- which adopt
// now rejects outright rather than resolving, so the disagreement is
// unreachable through the API too.
//
// Left as-is rather than aligned: the fallback is legacy-only now. Every conf
// saved from here on carries a real tag (see the useState below), so this
// branch runs once per pre-tag conf and then never again for it.
const duckTypeRecruitmentType = (localData: any) => {
  if (localData?.type) {
    return localData.type;
  } else if (localData?.arms) {
    return 'pipeline_experiment';
  } else if (localData?.ad_campaign_name_base) {
    return 'destination';
  } else {
    return 'simple';
  }
};

const Recruitment: React.FC<Props> = ({ id, globalData, localData }: Props) => {
  const [recruitmentType, setRecruitmentType] = useState<string>(
    duckTypeRecruitmentType(localData)
  );

  const initialState: any[] = [
    {
      end_date: '2024-01-07T00:00',
      start_date: '2024-01-01T00:00',
      ad_campaign_name: '',
      objective: '',
      optimization_goal: '',
      min_budget: 1,
      budget: '',
      max_sample: '',
      type: 'simple',
      incentive_per_respondent: 0,
      efficiency_weight: 1,
    },
    {
      ad_campaign_name_base: '',
      objective: '',
      optimization_goal: '',
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
      efficiency_weight: 1,
    },
    {
      ad_campaign_name_base: '',
      objective: '',
      optimization_goal: '',
      min_budget: 1,
      budget_per_arm: '',
      end_date: '2024-01-07T00:00',
      start_date: '2024-01-01T00:00',
      max_sample_per_arm: '',
      type: 'destination',
      incentive_per_respondent: 0,
      efficiency_weight: 1,
    },
  ];

  // The tag is stamped onto localData rather than passed through untouched:
  // a conf stored before adopt tagged the union has none, and re-POSTing it
  // without one leaves the server inferring the arm from shape all over again.
  const [formData, setFormData] = useState<LocalData>(
    localData
      ? { ...localData, type: duckTypeRecruitmentType(localData) }
      : initialState.find((obj: any) => obj.type === recruitmentType)
  );
  const [error, setError] = useState<string | null>(null);

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
    if ('ad_campaign_name' in data) {
      data.ad_campaign_name = data.ad_campaign_name.trim();
    }

    if ('ad_campaign_name_base' in data) {
      data.ad_campaign_name_base = data.ad_campaign_name_base.trim();
    }

    return data;
  };

  const validateEfficiencyWeight = (data: LocalData): boolean => {
    if ('efficiency_weight' in data && data.efficiency_weight != null) {
      const value = Number(data.efficiency_weight);
      if (isNaN(value) || value < 0 || value > 1) {
        setError('Efficiency weight must be a number between 0 and 1');
        return false;
      }
    }
    return true;
  };

  const onSubmit = (e: any): void => {
    e.preventDefault();

    setError(null);

    if (!validateEfficiencyWeight(formData)) {
      return;
    }

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
          <Simple
            formData={formData as RecruitmentSimple}
            updateFormData={setFormData}
          />
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
        {error && <div className="mx-6 mt-4 text-sm text-red-600">{error}</div>}
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
