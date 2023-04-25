import { getField } from './getField';
import { translateField } from './translateField';
import { EventInterface, FormData } from '../types/form';
import { ConfBase, ConfObject, FieldBase, FieldState } from '../types/conf';

export const initialiseFieldState = (conf: ConfBase) => {
  return conf.fields.map((f: FieldBase) => translateField(f));
};

export const getFieldState = (conf: ConfObject, localFormData: FormData) => {
  return conf.fields.map((f: FieldBase) => translateField(f, localFormData));
};

export const updateFieldState = (
  state: FieldState[],
  event: EventInterface
) => {
  if (getField(state, event)) {
    getField(state, event).value = event.value;
  }

  return state;
};

export const updateGlobalState = (state: FieldState[], conf: ConfBase) => {
  // TODO add delete functionality
  return [...state, ...initialiseFieldState(conf)];
};
