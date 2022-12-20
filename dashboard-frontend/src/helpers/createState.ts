import { StudyFieldResource } from '../types/study';
import { findByKey } from './arrays';
import { getInitialValue } from './objects';

export const createInitialState = (conf: any) => {
  const { fields } = conf;

  const mapFieldsToStateArray = (fields: any[]) => {
    return fields.map((field: StudyFieldResource) => ({
      [field.name]: getInitialValue(field, 'type'),
    }));
  };

  const mapped = fields
    ? mapFieldsToStateArray(fields)
    : mapFieldsToStateArray(findByKey(conf, 'fields')[0][0]);

  const stateObj = fields
    ? Object.assign({}, ...mapped)
    : Object.assign({}, ...mapped);

  return stateObj;
};
