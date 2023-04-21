import { FieldState } from '../types/conf';
import { EventInterface } from '../types/form';

export const getField = (fieldState: FieldState[], event: EventInterface) => {
  const index = fieldState.findIndex(
    (field: FieldState, i: number) => `${field.name}-${i}` === event.name
  );

  return fieldState[index];
};
