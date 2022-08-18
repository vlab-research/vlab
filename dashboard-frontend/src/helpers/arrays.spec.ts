import { lastValue, arrayMerge } from './arrays';

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

  it('merges the properties of three matching array elements into another', () => {
    const arr1 = [{ name: 'foo' }, { name: 'bar' }, { name: 'baz' }];
    const arr2 = [
      { name: 'foo', data: 'abcd' },
      { name: 'bar', data: '!"·$' },
      { name: 'baz', data: '1234' },
    ];

    const expectation = [
      { name: 'foo', data: 'abcd' },
      { name: 'bar', data: '!"·$' },
      { name: 'baz', data: '1234' },
    ];
    const res = arrayMerge(arr1, arr2, 'name');

    expect(res).toStrictEqual(expectation);
  });
});
