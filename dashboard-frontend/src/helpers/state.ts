import { getField } from './getField';
import { translateField } from './translateField';
import { EventInterface, FormData } from '../types/form';
import { ConfBase, ConfObjectBase, Field, FieldState } from '../types/conf';

export const initialiseFieldState = (conf: ConfBase) => {
  return conf.fields.map((f: Field) => translateField(f));
};

export const getFieldState = (
  conf: ConfObjectBase,
  localFormData: FormData
) => {
  return conf.fields.map(f => translateField(f, localFormData));
};

export const updateFieldState = (
  state: FieldState[] | any,
  event: EventInterface,
  conf?: ConfBase
) => {
  if (event.type === 'click' && conf) {
    return [...state, ...initialiseFieldState(conf)];
  }

  getField(state, event).value = event.value;

  return state;
};
