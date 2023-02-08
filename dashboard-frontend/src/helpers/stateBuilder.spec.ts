import { stateBuilder } from './stateBuilder';
import textField from '../../mocks/text.json';
import selectField from '../../mocks/select.json';
import Select from '../pages/NewStudyPage/form/inputs/Select';
import Text from '../pages/NewStudyPage/form/inputs/Text';

describe('stateBuilder', () => {
  it('takes a single field object and returns a new object to represent state configured for rendering a form', () => {
    const expectation = {
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
    };

    const res = stateBuilder(textField);
    expect(res).toStrictEqual(expectation);

    const expectation2 = {
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
    };

    const res2 = stateBuilder(selectField);
    expect(res2).toStrictEqual(expectation2);
  });
});
