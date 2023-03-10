import { FieldState } from '../types/form';
import { Event } from './state';

export const getField = (state: any[], event: Event) => {
  const outerIndex = state.findIndex(fieldset =>
    fieldset.map((obj: FieldState) => obj.name === event.name)
  );

  const innerIndex = state[outerIndex].findIndex(
    (obj: FieldState) => obj.name === event.name
  );

  return state[outerIndex][innerIndex];
};
