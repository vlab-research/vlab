import { compareArrays } from './arrays';

export const findMatch = (obj: any, obj2: any) => {
  if (obj && obj2) {
    const keys1 = Object.keys(obj);
    const keys2 = Object.keys(obj2);
    return compareArrays(keys1, keys2);
  }
};
