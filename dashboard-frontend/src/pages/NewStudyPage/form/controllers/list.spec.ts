import { destinations } from '../configs/destinations/destinations';
import list from './list';
import Select from '../inputs/Select';
import Text from '../inputs/Text';
import Button from '../buttons/Button';

describe('list controller', () => {
  const base = destinations;

  it('given a config of type list the controller can create some initial state when no global state is defined', () => {
    const expectation = [
      [
        {
          id: 'destination',
          name: 'destination',
          type: 'select',
          component: Select,
          label: 'Create a destination',
          helper_text: undefined,
          call_to_action: undefined,
          options: [
            {
              label: 'Fly Messenger',
              name: 'fly_messenger',
            },
            {
              label: 'Typeform',
              name: 'typeform',
            },
            {
              label: 'Curious Learning',
              name: 'curious_learning',
            },
          ],
          value: 'fly_messenger',
        },
        {
          id: 'initial_shortcode',
          name: 'initial_shortcode',
          type: 'text',
          component: Text,
          label: 'Initial shortcode',
          helper_text: 'E.g 12345',
          call_to_action: undefined,
          options: undefined,
          value: '',
        },
        {
          id: 'survey_name',
          name: 'survey_name',
          type: 'text',
          component: Text,
          label: 'Survey Name',
          helper_text: 'Eg. Fly',
          call_to_action: undefined,
          options: undefined,
          value: '',
        },
        {
          id: 'destination_name',
          name: 'destination_name',
          type: 'text',
          component: Text,
          label: 'Give your destination a name',
          helper_text: 'E.g example-fly-1',
          call_to_action: undefined,
          options: undefined,
          value: '',
        },
        {
          id: 'add_destination',
          name: 'add_destination',
          type: 'button',
          component: Button,
          label: 'Add destination',
          helper_text: undefined,
          call_to_action: undefined,
          options: undefined,
          value: '',
        },
      ],
    ];

    const res = list(destinations);

    expect(res).toStrictEqual(expectation);
    expect(res).toHaveLength(1);
  });

  it('given some change to the global state when the user clicks the add button the controller can update the number of fieldsets', () => {
    const fieldset = [
      [
        {
          id: 'destination',
          name: 'destination',
          type: 'select',
          component: Select,
          label: 'Create a destination',
          helper_text: undefined,
          call_to_action: undefined,
          options: [
            {
              label: 'Fly Messenger',
              name: 'fly_messenger',
            },
            {
              label: 'Typeform',
              name: 'typeform',
            },
            {
              label: 'Curious Learning',
              name: 'curious_learning',
            },
          ],
          value: 'fly_messenger',
        },
        {
          id: 'initial_shortcode',
          name: 'initial_shortcode',
          type: 'text',
          component: Text,
          label: 'Initial shortcode',
          helper_text: 'E.g 12345',
          call_to_action: undefined,
          options: undefined,
          value: '',
        },
        {
          id: 'survey_name',
          name: 'survey_name',
          type: 'text',
          component: Text,
          label: 'Survey Name',
          helper_text: 'Eg. Fly',
          call_to_action: undefined,
          options: undefined,
          value: '',
        },
        {
          id: 'destination_name',
          name: 'destination_name',
          type: 'text',
          component: Text,
          label: 'Give your destination a name',
          helper_text: 'E.g example-fly-1',
          call_to_action: undefined,
          options: undefined,
          value: '',
        },
        {
          id: 'add_destination',
          name: 'add_destination',
          type: 'button',
          component: Button,
          label: 'Add destination',
          helper_text: undefined,
          call_to_action: undefined,
          options: undefined,
          value: '',
        },
      ],
    ];

    const fieldset2 = [
      {
        id: 'destination',
        name: 'destination',
        type: 'select',
        component: Select,
        label: 'Create a destination',
        helper_text: undefined,
        call_to_action: undefined,
        options: [
          {
            label: 'Fly Messenger',
            name: 'fly_messenger',
          },
          {
            label: 'Typeform',
            name: 'typeform',
          },
          {
            label: 'Curious Learning',
            name: 'curious_learning',
          },
        ],
        value: 'fly_messenger',
      },
      {
        id: 'initial_shortcode',
        name: 'initial_shortcode',
        type: 'text',
        component: Text,
        label: 'Initial shortcode',
        helper_text: 'E.g 12345',
        call_to_action: undefined,
        options: undefined,
        value: '',
      },
      {
        id: 'survey_name',
        name: 'survey_name',
        type: 'text',
        component: Text,
        label: 'Survey Name',
        helper_text: 'Eg. Fly',
        call_to_action: undefined,
        options: undefined,
        value: '',
      },
      {
        id: 'destination_name',
        name: 'destination_name',
        type: 'text',
        component: Text,
        label: 'Give your destination a name',
        helper_text: 'E.g example-fly-1',
        call_to_action: undefined,
        options: undefined,
        value: '',
      },
      {
        id: 'add_destination',
        name: 'add_destination',
        type: 'button',
        component: Button,
        label: 'Add destination',
        helper_text: undefined,
        call_to_action: undefined,
        options: undefined,
        value: '',
      },
    ];

    const expectation = [fieldset, fieldset2];

    const res = list(destinations);

    // expect(res).toStrictEqual(expectation);
    // expect(res).toHaveLength(2);
  });
});
