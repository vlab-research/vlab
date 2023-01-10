import {
  mapValueToKey,
  getInitialValue,
  assignObject,
  getValueByProp,
  stringLookup,
  isJSON,
} from './objects';

describe('mapValueToKey', () => {
  it('takes a value, a key and a config and returns a single object', () => {
    const config = {
      title: 'Foo',
      description: 'bar',
      fields: [
        {
          name: 'foobar',
          type: 'text',
          label: 'Foobar',
          helper_text: 'foobar',
        },
      ],
    };
    const value = 'baz';
    const key = 'foo';

    const expectation = {
      value,
      key,
      config,
    };

    const res = mapValueToKey(value, key, config);
    expect(res).toStrictEqual(expectation);
  });
});

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

describe('assignObject', () => {
  it('takes a string and makes it the key of a new object', () => {
    const str = 'foobar';
    const value = { foo: 0, bar: '' };

    const expectation = { foobar: { foo: 0, bar: '' } };

    const res = assignObject(str, value);
    expect(res).toStrictEqual(expectation);
  });
});

describe('getValueByProp', () => {
  it('takes a an object and returns the value of a given prop', () => {
    const obj = { name: 'foo' };

    const expectation = 'foo';

    const res = getValueByProp(obj, 'name');
    expect(res).toStrictEqual(expectation);
  });
});

describe('stringLookup', () => {
  it('takes a string and finds in an array the data object it belongs to', () => {
    const str = 'foobar';
    const arr = [{ name: 'foobar' }, { name: 'foobaz' }, { name: 'foobazzle' }];
    const key = 'name';

    const expectation = { name: 'foobar' };

    const res = stringLookup(str, arr, key);
    expect(res).toStrictEqual(expectation);
  });
});

describe('isJSONObject', () => {
  it('takes an object and checks if its JSON', () => {
    const obj = { name: 'John', age: 30, city: 'New York' };
    const myJSON = JSON.stringify(obj);

    const expectation = true;

    const res = isJSON(myJSON);
    expect(res).toStrictEqual(expectation);
  });
});
