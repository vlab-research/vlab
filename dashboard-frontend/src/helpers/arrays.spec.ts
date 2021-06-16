import { lastValue } from './arrays';

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
