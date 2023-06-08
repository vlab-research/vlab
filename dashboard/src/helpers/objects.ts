import { compareArrays } from './arrays';

export const validate = (obj: any, obj2: any) => {
  if (obj && obj2) {
    return compareArrays(Object.keys(obj), Object.keys(obj2));
  }
  return false;
};
