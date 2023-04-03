import { translateField, getInitialValue } from './translateField';
import Select from '../pages/NewStudyPage/components/form/inputs/Select';
import Text from '../pages/NewStudyPage/components/form/inputs/Text';
import text from '../../mocks/text';
import select from '../../mocks/select';
import number from '../../mocks/number';

describe('translateField', () => {
  it('given a field it returns a new object configured for rendering a form', () => {
    const expectation = {
      id: 'foo',
      name: 'foo',
      type: 'text',
      component: Text,
      label: 'Foo',
      helper_text: 'foo...',
      options: undefined,
      value: '',
    };

    const res = translateField(text);
    expect(res).toStrictEqual(expectation);

    const expectation2 = {
      id: 'bar',
      name: 'bar',
      type: 'select',
      component: Select,
      label: 'Bar',
      helper_text: undefined,
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
      value: 'foo',
    };

    const res2 = translateField(select);
    expect(res2).toStrictEqual(expectation2);

    const expectation3 = {
      id: 'baz',
      name: 'baz',
      type: 'number',
      component: Text,
      label: 'Baz',
      helper_text: 'baz...',
      options: undefined,
      value: 1,
    };
    const res3 = translateField(number);
    expect(res3).toStrictEqual(expectation3);
  });
});

describe('getInitialValue', () => {
  it('given a field it returns an initial value based on its type', () => {
    let res = getInitialValue(text);
    expect(res).toStrictEqual('');

    res = getInitialValue(number);
    expect(res).toStrictEqual(1);

    res = getInitialValue(select);
    expect(res).toStrictEqual('foo');
  });
});
