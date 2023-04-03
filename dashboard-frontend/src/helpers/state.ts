import { ConfBase, FieldState } from '../types/form';
import { getField } from './getField';
import { Conf } from '../types/conf';
import { translateField } from './translateField';

export type Event = {
  name: string;
  value: any;
  type: string;
};

export const initialiseFieldState = (conf: ConfBase) => {
  return conf.fields.map(f => translateField(f));
};

export const getFieldState = (conf: ConfBase, localFormData: Conf) => {
  return conf.fields.map(f => translateField(f, localFormData));
};

export const updateFieldState = (state: FieldState[], event: Event) => {
  const clone = [...state];

  getField(state, event).value = event.value;

  return clone;
};
