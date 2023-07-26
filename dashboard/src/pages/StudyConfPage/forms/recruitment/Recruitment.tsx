import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import Simple from './Simple';
import Destination from './Destination';
import PipelineExperiment from './PipelineExperiment';
import PrimaryButton from '../../../../components/PrimaryButton';
import recruitmentTypes from '../../../../fixtures/recruitment/types';
import { GlobalFormData } from '../../../../types/conf';
import useCreateStudyConf from '../../hooks/useCreateStudyConf';

interface Props {
  id: string;
  globalData: GlobalFormData;
  localData: any;
  confKeys: string[];
}

const Recruitment: React.FC<Props> = ({
  id,
  globalData,
  localData,
  confKeys,
}: Props) => {
  const [recruitmentType, setRecruitmentType] = useState<string>('simple');

  useEffect(() => {
    if (localData) {
      if (localData.arms) {
        setRecruitmentType('pipeline_experiment');
      } else if (localData.ad_campaign_name_base) {
        setRecruitmentType('destination');
      } else {
        setRecruitmentType('simple');
      }
    }
  }, [localData]);

  const initialState: any[] = [
    {
      end_date: '',
      start_date: '',
      ad_campaign_name: '',
      budget: 0,
      max_sample: 0,
      type: 'simple',
    },
    {
      ad_campaign_name_base: '',
      budget_per_arm: 0,
      end_date: '',
      max_sample_per_arm: 0,
      start_date: '',
      arms: 0,
      recruitment_days: 0,
      offset_days: 0,
      type: 'pipeline_experiment',
    },
    {
      destination: '',
      ad_campaign_name_base: '',
      budget_per_arm: 0,
      end_date: '',
      max_sample_per_arm: 0,
      start_date: '',
      type: 'destination',
    },
  ];

  const [formData, setFormData] = useState<any>(
    localData ? localData : initialState
  );

  const updateFormData = (d: any): void => {
    setFormData(d);
  };

  const handleSelectChange = (e: any) => {
    const { value } = e.target;
    setRecruitmentType(value);
    const fields = initialState.find((obj: any) => obj.type === value);
    updateFormData(fields);
  };

  const params = useParams<{ studySlug: string }>();

  const studySlug = params.studySlug;

  const { createStudyConf, isLoadingOnCreateStudyConf } = useCreateStudyConf(
    'Recruitment settings saved',
    studySlug,
    confKeys,
    'recruitment'
  );

  const onSubmit = (e: any): void => {
    e.preventDefault();

    const data = {
      [id]: formData,
    };

    createStudyConf({ data, studySlug });
  };

  return (
    <div className="md:grid md:grid-cols-3 md:gap-6">
      <div className="md:col-span-1">
        <div className="px-4 sm:px-0"></div>
      </div>
      <div className="mt-5 md:mt-0 md:col-span-2">
        <div className="px-4 py-3 bg-gray-50 sm:px-6">
          <div className="sm:my-4">
            <form onSubmit={onSubmit}>
              <div className="mb-8">
                <label className="my-2 block text-sm font-medium text-gray-700">
                  Select a recruitment type
                </label>
                <select
                  className="w-4/5 mt-1 block shadow-sm sm:text-sm rounded-md"
                  onChange={e => handleSelectChange(e)}
                  value={recruitmentType}
                >
                  {recruitmentTypes.map(
                    (option: { name: string; label: string }, i: number) => (
                      <option key={i} value={option.name}>
                        {option.label}
                      </option>
                    )
                  )}
                </select>
                {recruitmentType === 'simple' && (
                  <Simple formData={formData} updateFormData={updateFormData} />
                )}
                {recruitmentType === 'pipeline_experiment' && (
                  <PipelineExperiment
                    formData={formData}
                    updateFormData={updateFormData}
                  />
                )}
                {recruitmentType === 'destination' && (
                  <Destination
                    formData={formData}
                    updateFormData={updateFormData}
                    destinations={globalData.destinations}
                  />
                )}
              </div>
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
          </div>
        </div>
      </div>
    </div>
  );
};

export default Recruitment;
