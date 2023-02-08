import Select from '../pages/NewStudyPage/form/inputs/Select';
import Text from '../pages/NewStudyPage/form/inputs/Text';
import { createInitialState } from './createInitialState';

describe('createInitalState', () => {
  it('takes a config and returns an array of state objects', () => {
    const config = {
      type: 'configObject',
      title: 'Foo',
      description: 'foo',
      fields: [
        {
          name: 'foo',
          type: 'text',
          label: 'Foo',
          helper_text: 'foo',
        },
        {
          name: 'bar',
          type: 'select',
          label: 'Bar',
          defaultValue: 'Foobar',
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
        },
      ],
    };

    const expectation = [
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
        defaultValue: 'Foobar',
        call_to_action: undefined,
        options: [
          { name: 'foo', label: 'Foo' },
          { name: 'bar', label: 'Bar' },
          { name: 'baz', label: 'Baz' },
        ],
        value: '',
      },
    ];

    const res = createInitialState(config);
    expect(res).toStrictEqual(expectation);
  });
});
