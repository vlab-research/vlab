import d2lIntl from 'd2l-intl';

export const calculatePercentage = ({
  current,
  total,
}: {
  current: number;
  total: number;
}) => {
  if (!isValidNumber(current) || !isValidNumber(total)) {
    throw new InvalidNumberError();
  }

  if (total === 0) {
    throw new UnexpectedNumberError('`total` cannot be 0');
  }

  if (current > total) {
    throw new UnexpectedNumberError('`current` cannot be greater than `total`');
  }

  return round((current / total) * 100);
};

export const calculateAverage = (values: number[]) =>
  round(
    values.reduce((prev, current) => {
      if (!isValidNumber(current)) {
        throw new InvalidNumberError();
      }

      return prev + current;
    }, 0) / values.length
  );

export const round = (num: number) => {
  if (!isValidNumber(num)) {
    throw new InvalidNumberError();
  }

  return Number.parseFloat(num.toFixed(2));
};

export const INVALID_NUMBERS = [Infinity, -Infinity, NaN];

export class InvalidNumberError extends Error {
  constructor() {
    super('Invalid Number Error');
    Object.setPrototypeOf(this, InvalidNumberError.prototype);
  }
}

export const isValidNumber = (num: number) => {
  if (num === Infinity || num === -Infinity || isNaN(num)) {
    return false;
  }

  return true;
};

export class UnexpectedNumberError extends Error {
  constructor(public message: string) {
    super(message);
    Object.setPrototypeOf(this, UnexpectedNumberError.prototype);
  }
}

export const formatNumber = (num: number) =>
  new Intl.NumberFormat('en-US').format(num);

export const parseNumber = (formattedNumber: string) => {
  if (formattedNumber === '∞') {
    return Infinity;
  }

  if (formattedNumber === '-∞') {
    return -Infinity;
  }

  const parser = new d2lIntl.NumberParse('en-US');

  return parser.parse(formattedNumber);
};
