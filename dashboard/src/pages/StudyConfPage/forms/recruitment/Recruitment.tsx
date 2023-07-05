import React, { useEffect, useState } from 'react';
import Simple from './Simple';
import Destination from './Destination';
import PipelineExperiment from './PipelineExperiment';
import recruitmentTypes from '../../../../fixtures/recruitment/types';
import { GlobalFormData } from '../../../../types/conf';

interface SelectOption {
  name: string;
  label: string;
}

interface Props {
  id: string;
  globalData: GlobalFormData;
  localData: any;
}

const Recruitment: React.FC<Props> = ({ id, globalData, localData }: Props) => {
  const [recruitmentType, setRecruitmentType] = useState('simple');

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

  const handleChange = (e: any) => {
    setRecruitmentType(e.target.value);
  };

  const filterRecruitmentTypes = (arr: any[]) => {
    if (!globalData.destinations) {
      return arr.filter((t, i) => t.name !== 'destination');
    }
    return arr;
  };

  return (
    <div className="md:grid md:grid-cols-3 md:gap-6">
      <div className="md:col-span-1">
        <div className="px-4 sm:px-0"></div>
      </div>
      <div className="mt-5 md:mt-0 md:col-span-2">
        <div className="px-4 py-3 bg-gray-50 sm:px-6">
          <div className="sm:my-4">
            <label className="my-2 block text-sm font-medium text-gray-700">
              Select a recruitment type
            </label>
            <select
              className="w-4/5 mt-1 block shadow-sm sm:text-sm rounded-md"
              onChange={handleChange}
              value={recruitmentType}
            >
              {filterRecruitmentTypes(recruitmentTypes).map(
                (option: SelectOption, i: number) => (
                  <option key={i} value={option.name}>
                    {option.label || option.name}
                  </option>
                )
              )}
            </select>
          </div>
          {recruitmentType === 'simple' && <Simple id={id} data={localData} />}
          {recruitmentType === 'pipeline_experiment' && (
            <PipelineExperiment id={id} data={localData} />
          )}
          {recruitmentType === 'destination' && (
            <Destination
              id={id}
              data={localData}
              destinations={globalData.destinations}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default Recruitment;
