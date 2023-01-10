import { recruitment_simple } from './recruitment_simple';
import { recruitment_pipeline_experiment } from './recruitment_pipeline_experiment';
import { recruitment_destination_experiment } from './recruitment_destination_experiment';

export const recruitment = {
  type: 'configSelect',
  title: 'Recruitment',
  description:
    'The "recruitment" configuration describes how/where recruitment will take place. Every study needs to recruit from somewhere.',
  selector: {
    name: 'recruitment_type',
    type: 'select',
    label: 'Select a recruitment type',
    options: [
      recruitment_simple,
      recruitment_pipeline_experiment,
      recruitment_destination_experiment,
    ],
  },
};
