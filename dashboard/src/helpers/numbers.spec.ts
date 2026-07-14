import {
  calculateAverage,
  calculatePercentage,
  formatNumber,
  InvalidNumberError,
  INVALID_NUMBERS,
  parseNumber,
  round,
  UnexpectedNumberError,
} from './numbers';

describe('calculatePercentage', () => {
  it('returns the percentage between the two provided values', () => {
    expect(calculatePercentage({ current: 10, total: 100 })).toBe(10);
    expect(calculatePercentage({ current: 2, total: 10 })).toBe(20);
    expect(calculatePercentage({ current: 0, total: 10 })).toBe(0);
  });

  it('throws error when total is 0', () => {
    expect(() => calculatePercentage({ current: 0, total: 0 })).toThrow(
      new UnexpectedNumberError('`total` cannot be 0')
    );
  });

  it('throws error when current is greater than total', () => {
    expect(() => calculatePercentage({ current: 100, total: 10 })).toThrow(
      new UnexpectedNumberError('`current` cannot be greater than `total`')
    );
  });

  INVALID_NUMBERS.forEach(invalidNumber => {
    it(`throws error when current is ${invalidNumber}`, () => {
      expect(() => calculatePercentage({ current: invalidNumber, total: 100 })).toThrow(
        InvalidNumberError
      );
    });

    it(`throws error when total is ${invalidNumber}`, () => {
      expect(() => calculatePercentage({ current: 10, total: invalidNumber })).toThrow(
        InvalidNumberError
      );
    });
  });
});

describe('calculateAverage', () => {
  it('returns the average given an array of numbers', () => {
    expect(calculateAverage([1, 2, 3])).toBe(2);
    expect(calculateAverage([1.01, 1.02, 1.03])).toBe(1.02);
  });

  INVALID_NUMBERS.forEach(invalidNumber => {
    it(`throws error when any of the values provided is ${invalidNumber}`, () => {
      expect(() => calculateAverage([1, 2, invalidNumber])).toThrow(
        InvalidNumberError
      );
    });
  });
});

describe('round', () => {
  it('returns the given number rounded to two decimals', () => {
    expect(round(5.557)).toBe(5.56);
  });

  INVALID_NUMBERS.forEach(invalidNumber => {
    it(`throws error when the number provided is ${invalidNumber}`, () => {
      expect(() => round(invalidNumber)).toThrow(InvalidNumberError);
    });
  });
});

describe('formatNumbers', () => {
  it('can format a number in English from United States', () => {
    expect(formatNumber(0)).toBe('0');
    expect(formatNumber(55)).toBe('55');
    expect(formatNumber(999)).toBe('999');
    expect(formatNumber(1000)).toBe('1,000');
    expect(formatNumber(10000)).toBe('10,000');
    expect(formatNumber(100000)).toBe('100,000');
    expect(formatNumber(1222333)).toBe('1,222,333');
    expect(formatNumber(-1222333)).toBe('-1,222,333');
    expect(formatNumber(-1222333.37)).toBe('-1,222,333.37');
    expect(formatNumber(NaN)).toBe('NaN');
    expect(formatNumber(Infinity)).toBe('∞');
    expect(formatNumber(-Infinity)).toBe('-∞');
  });
});

describe('parseNumber', () => {
  it('can parse a number that has been formatted by "formatNumbers" helper', () => {
    expect(parseNumber(formatNumber(0))).toBe(0);
    expect(parseNumber(formatNumber(55))).toBe(55);
    expect(parseNumber(formatNumber(999))).toBe(999);
    expect(parseNumber(formatNumber(1000))).toBe(1000);
    expect(parseNumber(formatNumber(10000))).toBe(10000);
    expect(parseNumber(formatNumber(100000))).toBe(100000);
    expect(parseNumber(formatNumber(1222333))).toBe(1222333);
    expect(parseNumber(formatNumber(-1222333))).toBe(-1222333);
    expect(parseNumber(formatNumber(-1222333.37))).toBe(-1222333.37);

    expect(parseNumber(formatNumber(NaN))).toBe(NaN);
    expect(parseNumber(formatNumber(Infinity))).toBe(Infinity);
    expect(parseNumber(formatNumber(-Infinity))).toBe(-Infinity);
  });
});
