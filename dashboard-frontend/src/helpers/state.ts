import { ConfBase, ConfObjectBase, Field, FieldState } from '../types/conf';
import { EventInterface } from '../types/form';
import { getField } from './getField';
import { translateField } from './translateField';

export const initialiseFieldState = (conf: ConfBase) => {
  return conf.fields.map((f: Field) => translateField(f));
};

export const getFieldState = (
  conf: ConfObjectBase,
  localFormData: FormData | FormData[]
) => {
  return conf.fields.map(f => translateField(f, localFormData));
};

export const updateFieldState = (
  conf: ConfBase,
  state: FieldState[],
  event: EventInterface
) => {
  const clone = [...state];

  if (event.type === 'click') {
    return [...clone, initialiseFieldState(conf)];
  }

  getField(state, event).value = event.value;

  return clone;
};
