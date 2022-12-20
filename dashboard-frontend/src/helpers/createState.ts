import { StudyFieldResource } from '../types/study';
import { findByKey } from './arrays';
import { getInitialValue } from './objects';

// returns an initial state
// mirrors formBuilder API
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

  // const nestedConfKey = Object.keys(conf)[0];

  const stateObj = fields
    ? Object.assign({}, ...mapped)
    : Object.assign({}, ...mapped);

  return stateObj;
};

// export const createStateFromTuple = (tuple: string | any[]) => {
//   // const confKey = tuple[0];
//   const conf = tuple[1];
//   return createInitialState(conf);
// };

// export const createStateFromArrayOfTuples = (arrOfTuples: any[]) => {
//   const mapped = arrOfTuples.map((confArr: string | any[]) =>
//     createStateFromTuple(confArr)
//   );

//   return Object.assign({}, ...mapped);
// };
