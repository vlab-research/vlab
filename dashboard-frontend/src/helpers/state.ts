import { Config, FieldState } from '../types/form';
import { formBuilder } from './formBuilder';
import { getField } from './getField';

export type Event = {
  name: string;
  value: any;
  type: string;
};

export const initialiseGlobalState = (config: Config) => {
  return [config.fields?.map(formBuilder)];
};

export const updateLocalState = (state: any[], event: Event) => {
  const clone = [...state];

  // state is now a fieldset
  // so an arr of arrs
  // we need to map over the arr of arrs to get the indices of the field and the fieldset

  getField(state, event).value = event.value;

  return clone;
};
