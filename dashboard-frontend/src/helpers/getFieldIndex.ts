import { FieldState } from '../types/form';
import { Event } from './state';

export const getFieldIndex = (state: FieldState[], event: Event) => {
  return state.findIndex((obj: any) => obj.name === event.name);
};
