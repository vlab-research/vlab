import {
  getFieldState,
  initialiseFieldState,
  updateFieldState,
} from '../../../helpers/state';
import { EventInterface, FormData } from '../../../types/form';
import { ConfObjectBase, FieldState } from '../../../types/conf';

const list = (
  conf: ConfObjectBase,
  localFormData?: FormData[],
  event?: EventInterface,
  fieldState?: FieldState[]
) => {
  if (!localFormData && !fieldState && !event) {
    return initialiseFieldState(conf);
  }

  if (localFormData && !fieldState && !event) {
    return localFormData.map(d => getFieldState(conf, d));
  }

  if (!localFormData && fieldState && event) {
    return updateFieldState(fieldState, event, conf);
  }

  if (localFormData && fieldState && event) {
    return updateFieldState(fieldState, event, conf);
  }

  return;
};

export default list;
