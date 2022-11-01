import { arrayMerge, arrToObj, lastValue, findByKey } from './arrays';

describe('lastValue', () => {
  it('returns last value of a given array', () => {
    expect(lastValue([1, 2, 3])).toBe(3);
    expect(lastValue([1, 2])).toBe(2);
    expect(lastValue([1])).toBe(1);
  });

  it('returns undefined when the given array is empty', () => {
    expect(lastValue([])).toBe(undefined);
  });
});

describe('arrayMerge', () => {
  it('returns arr1 if arr2 is empty', () => {
    const arr1 = [{ name: 'foo' }, { name: 'bar' }, { name: 'baz' }];
    const arr2 = [{}];
    const res = arrayMerge(arr1, arr2, 'name');
    expect(res).toEqual(arr1);
  });

  it('merges the properties of one matching array element into another', () => {
    const arr1 = [{ name: 'foo' }, { name: 'bar' }, { name: 'baz' }];
    const arr2 = [{ name: 'foo', data: 'abcd' }];

    const expectation = [
      { name: 'foo', data: 'abcd' },
      { name: 'bar' },
      { name: 'baz' },
    ];
    const res = arrayMerge(arr1, arr2, 'name');

    expect(res).toStrictEqual(expectation);
  });

  it('merges the properties of two matching array elements into another', () => {
    const arr1 = [{ name: 'foo' }, { name: 'bar' }, { name: 'baz' }];
    const arr2 = [
      { name: 'foo', data: 'abcd' },
      { name: 'baz', data: '1234' },
    ];

    const expectation = [
      { name: 'foo', data: 'abcd' },
      { name: 'bar' },
      { name: 'baz', data: '1234' },
    ];
    const res = arrayMerge(arr1, arr2, 'name');

    expect(res).toStrictEqual(expectation);
  });
});

describe('arrToObj', () => {
  it('returns an array if array is empty', () => {
    const arr: any[] = [];
    const val = '';
    const res = arrToObj(arr, val);

    expect(res).toEqual(arr);
  });

  it('takes an array of objects and returns each value as a key in a new object', () => {
    const arr = ['foo', 'bar', 'baz'];
    const val = '';
    const res = arrToObj(arr, val);
    const expectation = { foo: '', bar: '', baz: '' };

    expect(res).toEqual(expectation);
  });
});

describe('findByKey', () => {
  it('recurses an array of objects to return all values for a given key', () => {
    const arr: any[] = [
      { name: 'foo' },
      { name: 'bar' },
      {
        someOtherProp: {
          name: 'baz',
        },
      },
    ];
    const key = 'name';
    const res = arr.map(obj => findByKey(obj, key));

    const expectation = [['foo'], ['bar'], [['baz']]];
    expect(res).toEqual(expectation);
  });

  it('recurses an array of complex data objects to return all values for a given key', () => {
    const arr: any = [
      { name: 'foo' },
      { name: 'bar' },
      {
        someOtherProp: {
          a: { name: 'baz' },
          b: { name: 'foobar' },
          c: { name: 'foobaz' },
        },
      },
    ];
    const key = 'name';
    const res = arr.map((obj: any) => findByKey(obj, key));

    const expectation = [['foo'], ['bar'], [[['baz'], ['foobar'], ['foobaz']]]];
    expect(res).toEqual(expectation);
  });
});
