import { curious_learning } from './curious_learning';
import { fly_messenger_destination } from './fly_messenger_destination';
import { typeform } from './typeform';

export const destinations = {
  type: 'config-multi',
  title: 'Destinations',
  description:
    'Every study needs a destination, where do the recruitment ads send the users?',
  selector: {
    name: 'destinations',
    type: 'configList',
    label: 'Select a destination type',
    options: [fly_messenger_destination, typeform, curious_learning], // these are just destination types
    callToAction: 'Save destination',
  },
  fields: [
    {
      name: 'destination_name',
      type: 'text',
      label: 'Give your destination a name',
      helperText: 'E.g example-fly-1',
    },
  ],
  list: {
    name: 'saved_destinations',
    type: 'list',
    label: 'Saved destinations',
    callToAction: 'Add destination',
  },
};

export default destinations;
