import { Config, FieldState } from '../types/form';
import { formBuilder } from './formBuilder';

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
  // TODO create a helper for getting the inner and outer index!

  const outerIndex = clone.findIndex(fieldset =>
    fieldset.map((obj: FieldState) => obj.name === event.name)
  );

  const innerIndex = clone[outerIndex].findIndex(
    (obj: FieldState) => obj.name === event.name
  );

  clone[outerIndex][innerIndex].value = event.value;

  return clone;
};
