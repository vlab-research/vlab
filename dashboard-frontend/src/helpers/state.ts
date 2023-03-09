import { Config, FieldState } from '../types/form';
import { formBuilder } from './formBuilder';

export type Event = {
  name: string;
  value: any;
  type: string;
};

export const initialiseGlobalState = (configs: Config[]) => {
  return configs.map(config => {
    return config.fields?.map(formBuilder);
  });
};

export const updateLocalState = (state: FieldState[][], event: Event) => {
  const clone = [...state];
  console.log(clone);

  // state is now a fieldset
  // so an arr of arrs
  // we need to map over the arr of arrs to get the indices of the field and the fieldset

  const outerIndex = clone.findIndex(fieldset =>
    fieldset.map((obj: any) => obj.name === event.name)
  );

  const innerIndex = clone.findIndex((obj: any) => obj.name === event.name);

  clone[outerIndex][innerIndex].value = event.value;

  return clone;
};
