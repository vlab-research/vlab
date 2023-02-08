import { updateLocalState, Event } from './updateLocalState';
import Text from '../pages/NewStudyPage/form/inputs/Text';
import Select from '../pages/NewStudyPage/form/inputs/Select';
import { FieldState } from '../types/form';

describe('updateLocalState', () => {
  it('takes an array of state objects and uses event data to update the value key of the target object', () => {
    const state: FieldState[] = [
      {
        id: 'foo',
        name: 'foo',
        type: 'text',
        component: Text,
        label: 'Foo',
        helper_text: 'foo',
        defaultValue: undefined,
        call_to_action: undefined,
        options: undefined,
        value: '',
      },
      {
        id: 'bar',
        name: 'bar',
        type: 'select',
        component: Select,
        label: 'Bar',
        helper_text: undefined,
        defaultValue: undefined,
        call_to_action: undefined,
        options: [
          {
            name: 'foo',
            label: 'Foo',
          },
          {
            name: 'bar',
            label: 'Bar',
          },
          {
            name: 'baz',
            label: 'Baz',
          },
        ],
        value: '',
      },
    ];

    const event: Event = { name: 'foo', value: 'foobaz' };

    const newState: FieldState[] = [
      {
        id: 'foo',
        name: 'foo',
        type: 'text',
        component: Text,
        label: 'Foo',
        helper_text: 'foo',
        defaultValue: undefined,
        call_to_action: undefined,
        options: undefined,
        value: 'foobaz',
      },
      {
        id: 'bar',
        name: 'bar',
        type: 'select',
        component: Select,
        label: 'Bar',
        helper_text: undefined,
        defaultValue: undefined,
        call_to_action: undefined,
        options: [
          {
            name: 'foo',
            label: 'Foo',
          },
          {
            name: 'bar',
            label: 'Bar',
          },
          {
            name: 'baz',
            label: 'Baz',
          },
        ],
        value: '',
      },
    ];

    const expectation: FieldState[] = newState;

    const res = updateLocalState(state, event);
    expect(res).toStrictEqual(expectation);
  });
});
