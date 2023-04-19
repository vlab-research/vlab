export const lastValue = <T>(values: T[]): T => values[values.length - 1];

export const reduceFieldStateToAnObject = (arr: any[]) => {
  return arr.reduce(
    (obj: any, item: any) => ({ ...obj, [item.name]: item.value }),
    {}
  );
};

export const reorderArray = (prevArr: any[], element: any) => {
  return [...prevArr.filter(a => a !== element), element];
};
