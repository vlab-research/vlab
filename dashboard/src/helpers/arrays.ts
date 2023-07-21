export const lastValue = <T>(values: T[]): T => values[values.length - 1];

export const reduceFieldStateToAnObject = (arr: any[]) => {
  return arr.reduce(
    (obj: any, item: any) => ({ ...obj, [item.name]: item.value }),
    {}
  );
};

export const getFirstOption = (arr: any[]) => {
  return arr[0].name;
};

export const isLastElement = (arr: any[], element: any) => {
  if (!Array.isArray(arr)) {
    throw new Error('First argument must be an array.');
  }

  const lastIndex = arr.length - 1;
  return arr[lastIndex] === element;
};

export const compareArrays = (a: any[], b: any[]) =>
  a.length === b.length &&
  a.every((element: any, index: number) => element === b[index]);
