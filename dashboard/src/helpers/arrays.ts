export const lastValue = <T>(values: T[]): T => values[values.length - 1];

export const reduceFieldStateToAnObject = (arr: any[]) => {
  return arr.reduce(
    (obj: any, item: any) => ({ ...obj, [item.name]: item.value }),
    {}
  );
};
