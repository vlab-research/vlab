import { StudyFieldResource } from '../types/study';
import { formBuilder } from './formBuilder';

export const getFormFields = (fields: StudyFieldResource[]) => {
  return fields.map(formBuilder);
};
