import { StudyFieldResource } from '../types/study';
import { findByKey } from './arrays';
import { getInitialValue } from './objects';

export const createInitialState = (fields: any[]) => {
  const mapFieldsToStateArray = (fields: any[]) => {
    return fields.map((field: StudyFieldResource) => ({
      [field.name]: getInitialValue(field, 'type'),
    }));
  };

  const mapped = fields && mapFieldsToStateArray(fields);

  // console.log(findByKey(conf, 'fields')[0]);

  const stateObj = fields && Object.assign({}, ...mapped);

  return stateObj;
};
