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

export const isLast = (arr: any[], el: any) => {
  const index = arr.indexOf(el);
  if (index === arr.length - 1) {
    return true;
  } else {
    return false;
  }
};
export const compareArrays = (a: any[], b: any[]) =>
  a.length === b.length &&
  a.every((element: any, index: number) => element === b[index]);
