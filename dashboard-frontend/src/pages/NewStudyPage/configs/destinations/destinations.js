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
    type: 'list',
    label: 'Add new destination',
    options: [fly_messenger_destination, typeform, curious_learning],
  },
};

export default destinations;
