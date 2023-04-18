import simple from '../../src/pages/StudyConfPage/confs/recruitment/simple';
import pipeline_experiment from '../../src/pages/StudyConfPage/confs/recruitment/pipeline_experiment';
import destination from '../../src/pages/StudyConfPage/confs/recruitment/destination';

const translatedConf = {
  type: 'confSelect',
  title: 'Recruitment',
  description:
    'The "recruitment" configuration describes how/where recruitment will take place. Every study needs to recruit from somewhere.',
  fields: [
    {
      name: 'recruitment_type',
      type: 'select',
      label: 'Select a recruitment type',
      options: [simple, pipeline_experiment, destination],
    },
    {
      name: 'ad_campaign_name',
      type: 'text',
      label: 'Ad campaign name',
      helper_text: 'E.g vlab-vaping-pilot-2',
    },
    {
      name: 'budget',
      type: 'number',
      label: 'Budget',
      helper_text: 'E.g 8400',
    },
    {
      name: 'max_sample',
      type: 'number',
      label: 'Maximum sample',
      helper_text: 'E.g 1000',
    },
    {
      name: 'start_date',
      type: 'text',
      label: 'Start date',
      helper_text: 'E.g 2022-01-10',
    },
    {
      name: 'end_date',
      type: 'text',
      label: 'End date',
      helper_text: 'E.g 2022-01-31',
    },
  ],
};

export default translatedConf;
