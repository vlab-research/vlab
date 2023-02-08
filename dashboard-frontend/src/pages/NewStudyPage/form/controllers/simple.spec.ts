import { general } from '../configs/general';
import simple from './simple';
import Text from './simple';

describe('simple', () => {
  it('takes a config, a state, an event and returns a new state configured for rendering a form', () => {
    const config = general;

    const state = [
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
    ];

    const event = { name: 'foo', value: 'baz' };

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
        value: 'baz',
      },
    ];
    const res = simple(config, state, event);

    expect(res).toStrictEqual(expectation);
  });
});
