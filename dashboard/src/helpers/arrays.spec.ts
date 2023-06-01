import { compareArrays, lastValue, reduceFieldStateToAnObject } from './arrays';

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

describe('reduceFieldStateToAnObject', () => {
  it('takes an array of field states and reduces them to a single object. Each name becomes a key and and each key is assigned to a value', () => {
    const states = [
      { name: 'foo', value: 'foobar' },
      { name: 'baz', someFieldName: 'bazza', value: 'bazzle' },
    ];

    const expectation = { foo: 'foobar', baz: 'bazzle' };

    const res = reduceFieldStateToAnObject(states);

    expect(res).toStrictEqual(expectation);
  });
});

describe('compareArrays', () => {
  it('takes two arrays and checks for equality', () => {
    const arr1 = [1, 2, 3];
    const arr2 = [1, 2, 3];

    const res = compareArrays(arr1, arr2);

    expect(res).toBe(true);
  });
});
