export const lastValue = <T>(values: T[]): T => values[values.length - 1];

interface Arr1 {
  name: string;
}

interface Arr2 extends Arr1 {
  data: string;
}

export const arrayMerge = (arr1: Arr1[], arr2: Arr2[] | any, key: string) => {
  if (arr2.length > 0) {
    return arr1.map(el => matcher(el, arr2, key));
  }
  return arr1;
};

const matcher = (el: any, arr2: [], key: string) => {
  for (let i = 0; i < arr2.length; i++) {
    if (el[key] === arr2[i][key]) {
      return arr2[i];
    }
  }
  return el;
};

export const arrToObj = (arr: any[], val: any): {} => {
  if (arr.length > 0) {
    const mapped = arr.map(str => ({ [str]: val }));
    return Object.assign({}, ...mapped);
  }
  return [];
};

export const findByKey = (obj: any, key: string) => {
  let values: any[] = [];

  obj &&
    Object.keys(obj).forEach(k => {
      if (k === key) {
        values.push(obj[k]);
      } else {
        if (typeof obj[k] === 'object') {
          values.push(findByKey(obj[k], key));
        }
        return null;
      }
      return values;
    });
  return values;
};

export const reorderArray = (arr: any[], start: number, numItems: number) => {
  const duplicateArr = [...arr];
  const target = duplicateArr.splice(start, numItems);
  target.map((el: any) => duplicateArr.push(el));
  return duplicateArr;
};
