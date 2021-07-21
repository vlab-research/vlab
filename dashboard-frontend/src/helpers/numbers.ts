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

export const calculateAverageDeviation = (values: number[]) => {
  const centralPoint = calculateAverage(values);

  const absoluteDeviationsFromCentralPoint = values.map(value =>
    Math.abs(centralPoint - value)
  );

  const averageDeviation = calculateAverage(absoluteDeviationsFromCentralPoint);

  return round(averageDeviation);
};

export const calculateAverage = (values: number[]) =>
  values.reduce((prev, current) => {
    if (!isValidNumber(current)) {
      throw new InvalidNumberError();
    }

    return prev + current;
  }, 0) / values.length;

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