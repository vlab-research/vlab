import { ConfObjectBase, EventInterface, FieldState } from '../types/form';
import { getField } from './getField';
import { Conf } from '../types/conf';
import { translateField } from './translateField';

export const initialiseFieldState = (conf: ConfObjectBase) => {
  return conf.fields.map(f => translateField(f));
};

export const getFieldState = (conf: ConfObjectBase, localFormData: Conf) => {
  return conf.fields.map(f => translateField(f, localFormData));
};

export const updateFieldState = (
  state: FieldState[],
  event: EventInterface
) => {
  const clone = [...state];

  getField(state, event).value = event.value;

  return clone;
};
