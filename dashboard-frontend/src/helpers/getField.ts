import { FieldState } from '../types/form';
import { Event } from './state';

export const getField = (fields: FieldState[], event: Event) => {
  const index = fields.findIndex(
    (field: FieldState) => field.name === event.name
  );

  return fields[index];
};
