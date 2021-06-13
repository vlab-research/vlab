import {
  calculateAverage,
  calculateAverageDeviation,
  calculatePercentage,
  InvalidNumberError,
  INVALID_NUMBERS,
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
    try {
      expect.assertions(2);
      calculatePercentage({ current: 0, total: 0 });
    } catch (err) {
      expect(err).toBeInstanceOf(UnexpectedNumberError);
      expect(err.message).toBe('`total` cannot be 0');
    }
  });

  it('throws error when current is greater than total', () => {
    try {
      expect.assertions(2);
      calculatePercentage({ current: 100, total: 10 });
    } catch (err) {
      expect(err).toBeInstanceOf(UnexpectedNumberError);
      expect(err.message).toBe('`current` cannot be greater than `total`');
    }
  });

  INVALID_NUMBERS.forEach(invalidNumber => {
    it(`throws error when any of the values provided is ${invalidNumber}`, () => {
      expect.assertions(2);

      try {
        calculatePercentage({ current: invalidNumber, total: 100 });
      } catch (err) {
        expect(err).toBeInstanceOf(InvalidNumberError);
      }

      try {
        calculatePercentage({ current: 10, total: invalidNumber });
      } catch (err) {
        expect(err).toBeInstanceOf(InvalidNumberError);
      }
    });
  });
});

describe('calculateAverageDeviation', () => {
  it('returns the average deviation given an array of numbers', () => {
    expect(calculateAverageDeviation([1, 2, 3])).toBe(0.67);
  });

  INVALID_NUMBERS.forEach(invalidNumber => {
    it(`throws error when any of the values provided is ${invalidNumber}`, () => {
      try {
        expect.assertions(1);
        calculateAverageDeviation([1, 2, invalidNumber]);
      } catch (err) {
        expect(err).toBeInstanceOf(InvalidNumberError);
      }
    });
  });
});

describe('calculateAverage', () => {
  it('returns the average given an array of numbers', () => {
    expect(calculateAverage([1, 2, 3])).toBe(2);
  });

  INVALID_NUMBERS.forEach(invalidNumber => {
    it(`throws error when any of the values provided is ${invalidNumber}`, () => {
      try {
        expect.assertions(1);
        calculateAverage([1, 2, invalidNumber]);
      } catch (err) {
        expect(err).toBeInstanceOf(InvalidNumberError);
      }
    });
  });
});

describe('round', () => {
  it('returns the given number rounded to two decimals', () => {
    expect(round(5.557)).toBe(5.56);
  });

  INVALID_NUMBERS.forEach(invalidNumber => {
    it(`throws error when the number provided is ${invalidNumber}`, () => {
      try {
        expect.assertions(1);
        round(invalidNumber);
      } catch (err) {
        expect(err).toBeInstanceOf(InvalidNumberError);
      }
    });
  });
});
