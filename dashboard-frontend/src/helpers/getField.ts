import { FieldState, EventInterface } from '../types/form';

export const getField = (fields: FieldState[], event: EventInterface) => {
  const index = fields.findIndex(
    (field: FieldState) => field.name === event.name
  );

  return fields[index];
};
