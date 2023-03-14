import { FieldState } from '../types/form';
import { Event } from './state';

export const getField = (state: FieldState[], event: Event) => {
  const index = state.findIndex(
    (field: FieldState) => field.name === event.name
  );

  return state[index];
};
