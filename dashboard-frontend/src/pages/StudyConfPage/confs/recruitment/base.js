import simple from './simple';
import pipeline_experiment from './pipeline_experiment';
import destination from './destination';

const recruitment = {
  type: 'confSelect',
  title: 'Recruitment',
  description:
    'The "recruitment" configuration describes how/where recruitment will take place. Every study needs to recruit from somewhere.',
  selector: {
    name: 'recruitment_type',
    type: 'select',
    label: 'Select a recruitment type',
    options: [simple, pipeline_experiment, destination],
  },
};

export default recruitment;
