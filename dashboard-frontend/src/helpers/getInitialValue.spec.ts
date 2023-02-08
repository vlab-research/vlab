import { getInitialValue } from './getInitialValue';

describe('getInitialValue', () => {
  it('takes an object and returns an initial value based on a given key', () => {
    const textField = {
      name: 'foo',
      type: 'text',
      label: 'Foo',
      helper_text: 'baz',
    };

    const emptyString = '';

    let res = getInitialValue(textField, 'type');

    expect(res).toStrictEqual(emptyString);

    const numberField = {
      name: 'bar',
      type: 'number',
      label: 'Bar',
      helper_text: 'foobaz',
    };

    const zero = 0;

    res = getInitialValue(numberField, 'type');

    expect(res).toStrictEqual(zero);

    const selectField = {
      name: 'bar',
      type: 'select',
      label: 'Bar',
      helper_text: 'foobaz',
    };

    const emptyString2 = '';

    res = getInitialValue(selectField, 'type');

    expect(res).toStrictEqual(emptyString2);
  });
});
