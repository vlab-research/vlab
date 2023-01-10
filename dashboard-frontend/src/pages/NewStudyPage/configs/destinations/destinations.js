import { curious_learning } from './curious_learning';
import { fly_messenger_destination } from './fly_messenger_destination';
import { typeform } from './typeform';

export const destinations = {
  type: 'configList',
  title: 'Destinations',
  description:
    'Every study needs a destination, where do the recruitment ads send the users?',
  list_label: 'Saved destinations',
  call_to_action: 'Add new destination',
  list_ref: 'destination_name',
  selector: {
    name: 'destination',
    type: 'select',
    label: 'Create a destination',
    options: [fly_messenger_destination, typeform, curious_learning], // could this be just a name and a source?
    call_to_action: 'Save',
  },
  fields: [
    {
      name: 'destination_name',
      type: 'text',
      label: 'Give your destination a name',
      helper_text: 'E.g example-fly-1',
    },
  ],
  // list: {
  //   name: 'saved_destinations',
  //   type: 'list',
  //   label: 'Saved destinations',
  //   call_to_action: 'Add new destination', // could these be moved to the top level?
  // },
};

export default destinations;
