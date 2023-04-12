import { app } from './app';
import { messenger } from './messenger';
import { web } from './web';

export const destinations = {
  type: 'confList',
  title: 'Destinations',
  description:
    'Every study needs a destination, where do the recruitment ads send the users?',
  fields: [
    {
      name: 'destination',
      label: 'Create a destination',
      type: 'fieldset',
      conf: {
        type: 'confSelect',
        title: 'Destinations',
        description:
          'The "recruitment" configuration describes how/where recruitment will take place. Every study needs to recruit from somewhere.',
        selector: {
          name: 'destination_type',
          type: 'select',
          label: 'Select a recruitment type',
          options: [messenger, web, app],
        },
      },
    },
    {
      name: 'name',
      type: 'text',
      label: 'Give your destination a name',
      helper_text: 'E.g example-fly-1',
    },
    {
      name: 'add_destination',
      type: 'button',
      label: 'Add destination',
      icon: 'plus',
    },
  ],
};

export default destinations;
