import list from './list';
import simpleList from '../confs/simpleList';
import destinations from '../confs/destinations/base';
import formData from '../../../../mocks/formData/formData';
import existingState from '../../../../mocks/state/existingState';
import Button from '../../NewStudyPage/components/form/inputs/Button';
import Text from '../../NewStudyPage/components/form/inputs/Text';
import { getField } from '../../../helpers/getField';
import Fieldset from '../../NewStudyPage/components/form/Fieldset';
import app from '../confs/destinations/app';
import messenger from '../confs/destinations/messenger';
import web from '../confs/destinations/web';

describe('list controller', () => {
  it('given a list conf it returns some initial fields when no state is defined', () => {
    const conf = simpleList;

    const expectation = [
      {
        id: 'foo',
        name: 'foo',
        type: 'text',
        component: Text,
        label: 'I am a list item',
        helper_text: 'Foo',
        options: undefined,
        value: '',
        conf: null,
      },
      {
        id: 'add_button',
        name: 'add_button',
        type: 'button',
        component: Button,
        label: undefined,
        helper_text: undefined,
        options: undefined,
        value: '',
        conf: null,
      },
    ];

    const res = list(conf);

    expect(res).toStrictEqual(expectation);
  });

  it('works for a list conf with nested confs', () => {
    const conf = destinations;

    const expectation = [
      {
        id: 'destination_create',
        name: 'destination_create',
        type: 'fieldset',
        component: Fieldset,
        label: 'Create a destination',
        helper_text: undefined,
        options: undefined,
        value: [],
        conf: {
          type: 'confSelect',
          title: 'Destinations',
          description:
            'Every study needs a destination, where do the recruitment ads send the users?',
          fields: [
            {
              name: 'destination_type',
              type: 'select',
              label: 'Select a destination type',
              options: [messenger, web, app],
            },
            {
              name: 'initial_shortcode',
              type: 'text',
              label: 'Initial shortcode',
              helper_text: 'E.g 12345',
            },
            {
              name: 'destination_name',
              type: 'text',
              label: 'Destination name',
              helper_text: 'E.g example-fly-1',
            },
          ],
        },
      },
      {
        id: 'add_button',
        name: 'add_button',
        type: 'button',
        component: Button,
        label: undefined,
        helper_text: undefined,
        options: undefined,
        value: '',
        conf: null,
      },
    ];

    const res = list(conf);

    expect(res).toStrictEqual(expectation);
  });

  it('given a list conf and some form data it returns a set of fields with their existing state', () => {
    const conf = simpleList;

    const localFormData = formData['simple_list'];

    const res = list(conf, localFormData);

    const expectation = [
      ...existingState[0]['simple_list'],
      {
        id: 'add_button',
        name: 'add_button',
        type: 'button',
        component: Button,
        label: undefined,
        helper_text: undefined,
        options: undefined,
        value: '',
        conf: null,
      },
    ];

    expect(res).toEqual(expectation);
  });

  it('given a list conf, some local form data and an event, it updates the value of the field on which the event occurred', () => {
    const conf = simpleList;

    const localFormData = formData['simple_list'];

    const state = [
      ...existingState[0]['simple_list'],
      {
        id: 'add_button',
        name: 'add_button',
        type: 'button',
        component: Button,
        label: undefined,
        helper_text: undefined,
        options: undefined,
        value: '',
        conf: null,
      },
    ];

    const event = {
      name: `foo-1`,
      value: 'bazzy',
      type: 'change',
      fieldType: 'text',
    };

    const newValue = event.value;
    const prevValue = formData['simple_list'][1]; // foobaz

    const res = list(conf, localFormData, event, state);

    const targetField = res && getField(res, event);

    expect(targetField?.value).toStrictEqual(newValue);
    expect(targetField?.value).not.toEqual(prevValue);
    expect(targetField?.value).toStrictEqual('bazzy');
  });

  it('works for click events too by adding a new field to the global state', () => {
    const conf = simpleList;

    const localFormData = formData['simple_list'];

    const state = [
      ...existingState[0]['simple_list'],
      {
        id: 'add_button',
        name: 'add_button',
        type: 'button',
        component: Button,
        label: undefined,
        helper_text: undefined,
        options: undefined,
        value: '',
        conf: null,
      },
    ];

    const event = {
      name: `add_button-3`,
      value: '',
      type: 'click',
      fieldType: 'button',
    };

    const prevLength = state.length; // 4

    const res = list(conf, localFormData, event, state);

    expect(res?.length).toStrictEqual(prevLength + 1); // 5
  });
});
