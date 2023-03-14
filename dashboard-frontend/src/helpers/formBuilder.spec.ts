import { formBuilder, getInitialValue } from './formBuilder';
import text from '../../mocks/fields/text.json';
import select from '../../mocks/fields/select.json';
import number from '../../mocks/fields/number.json';
import Select from '../pages/NewStudyPage/form/components/inputs/Select';
import Text from '../pages/NewStudyPage/form/components/inputs/Text';

describe('formBuilder', () => {
  it('given a field it returns a new object configured for rendering a form', () => {
    const expectation = {
      id: 'foo',
      name: 'foo',
      type: 'text',
      component: Text,
      label: 'Foo',
      helper_text: 'foo',
      options: undefined,
      value: '',
    };

    const res = formBuilder(text);
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

    const res2 = formBuilder(select);
    expect(res2).toStrictEqual(expectation2);
  });
});

describe('getInitialValue', () => {
  it('given a field it returns an initial value based on its type', () => {
    let res = getInitialValue(text);
    expect(res).toStrictEqual('');

    res = getInitialValue(number);
    expect(res).toStrictEqual(0);

    res = getInitialValue(select);
    expect(res).toStrictEqual('foo');
  });
});
