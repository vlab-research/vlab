import { Config, FieldState } from '../types/form';
import { formBuilder } from './formBuilder';

export type Event = {
  name: string;
  value: any;
};

export const initialiseGlobalState = (config: Config) => {
  return config.fields?.map(formBuilder);
};

export const updateLocalState = (state: FieldState[], event: Event) => {
  const clone = [...state];

  const index = clone.findIndex((obj: any) => obj.name === event.name);
  clone[index].value = event.value;

  return clone;
};
