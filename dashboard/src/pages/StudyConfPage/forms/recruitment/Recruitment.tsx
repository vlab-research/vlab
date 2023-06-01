import React, { useEffect, useState } from 'react';
import Simple from './Simple';
import Destination from './Destination';
import PipelineExperiment from './PipelineExperiment';
import recruitmentTypes from '../../../../fixtures/recruitment/types';

interface SelectOption {
  name: string;
  label: string;
}

interface Props {
  id: string;
  data: any;
}

const Recruitment: React.FC<Props> = ({ id, data }: Props) => {
  const [recruitmentType, setRecruitmentType] = useState('simple');

  useEffect(() => {
    if (data) {
      if (data.arms) {
        setRecruitmentType('pipeline_experiment');
      } else if (data.ad_campaign_name_base) {
        setRecruitmentType('destination');
      } else {
        setRecruitmentType('simple');
      }
    }
  }, [data]);

  const handleChange = (e: any) => {
    setRecruitmentType(e.target.value);
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
              {recruitmentTypes.map((option: SelectOption, i: number) => (
                <option key={i} value={option.name}>
                  {option.label || option.name}
                </option>
              ))}
            </select>
          </div>
          {recruitmentType === 'simple' && <Simple id={id} data={data} />}
          {recruitmentType === 'pipeline_experiment' && (
            <PipelineExperiment id={id} data={data} />
          )}
          {recruitmentType === 'destination' && (
            <Destination id={id} data={data} />
          )}
        </div>
      </div>
    </div>
  );
};

export default Recruitment;
