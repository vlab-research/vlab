export const reducer = (arr: any[]) => {
  return arr.reduce(
    (obj: any, item: any) => ({ ...obj, [item.name]: item.value }),
    {}
  );
};
