import { formBuilder } from './formBuilder';

export const getFormFields = fields => {
  return fields.map(formBuilder);
};
