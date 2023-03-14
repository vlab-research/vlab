import { Config, FieldState } from '../types/form';
import { formBuilder } from './formBuilder';
import { getField } from './getField';

export type Event = {
  name: string;
  value: any;
  type: string;
};

export const initialiseGlobalState = (config: Config) => {
  return config.fields?.map(formBuilder);
};

export const updateLocalState = (state: FieldState[], event: Event) => {
  const clone = [...state];

  getField(state, event).value = event.value;

  return clone;
};
