import { ConfBase, FieldState } from '../types/conf';
import { reduceFieldStateToAnObject } from './arrays';

export const getFormData = (conf: ConfBase, fieldState: FieldState[]) => {
  if (conf.type === 'confList') {
    const clone = [...fieldState].filter(fs => fs.type !== 'button');

    return clone.map(fs => {
      return fs.value;
    });
  }
  return { ...reduceFieldStateToAnObject(fieldState) };
};
