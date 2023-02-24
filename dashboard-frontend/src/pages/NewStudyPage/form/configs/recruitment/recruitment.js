import { recruitment_simple } from './recruitment_simple';
import { recruitment_pipeline } from './recruitment_pipeline';
import { recruitment_destination } from './recruitment_destination';

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
      recruitment_pipeline,
      recruitment_destination,
    ],
  },
};
