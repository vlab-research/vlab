import app from './app';
import messenger from './messenger';
import web from './web';

const destinations = {
  type: 'confList',
  title: 'Destinations',
  description: '',
  key: 'destination_create',
  input:
    // input is the only thing that repeats here
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
        fields: [
          {
            name: 'destination_name',
            type: 'text',
            label: 'Destination name',
            helper_text: 'E.g example-fly-1',
          },
        ],
      },
    },
  button: {
    name: 'add_button',
    type: 'button',
  },
};

export default destinations;
