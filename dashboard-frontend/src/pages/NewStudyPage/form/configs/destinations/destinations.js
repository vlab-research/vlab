import { curious_learning } from './curious_learning';
import { fly_messenger } from './fly_messenger';
import { typeform } from './typeform';

export const destinations = {
  type: 'configList',
  title: 'Destinations',
  description:
    'Every study needs a destination, where do the recruitment ads send the users?',
  selector: {
    name: 'destination',
    type: 'select',
    label: 'Create a destination',
    options: [fly_messenger, typeform, curious_learning], // could this be just a name and a source?
  },
  fields: [
    {
      name: 'destination_name',
      type: 'text',
      label: 'Give your destination a name',
      helper_text: 'E.g example-fly-1',
    },
    {
      name: 'add_destination',
      type: 'button',
      label: 'Add destination',
      // icon: "plus",
    },
  ],
};

export default destinations;
