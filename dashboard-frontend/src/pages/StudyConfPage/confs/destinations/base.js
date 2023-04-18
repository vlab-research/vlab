import app from './app';
import messenger from './messenger';
import web from './web';

const destinations = {
  type: 'confList',
  title: 'Destinations',
  description: '',
  fields: [
    {
      name: 'destination_create',
      label: 'Create a destination',
      type: 'fieldset',
      conf: {
        type: 'confSelect',
        title: 'Destinations',
        description:
          'Every study needs a destination, where do the recruitment ads send the users?',
        selector: {
          name: 'destination_type',
          type: 'select',
          label: 'Destination type',
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
    },
  ],
};

export default destinations;
