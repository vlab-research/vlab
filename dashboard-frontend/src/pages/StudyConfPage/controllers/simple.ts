import {
  initialiseFieldState,
  updateFieldState,
  getFieldState,
} from '../../../helpers/state';
import { ConfObject, FieldState } from '../../../types/conf';
import { EventInterface, FormData } from '../../../types/form';

const simple = (
  conf: ConfObject,
  localFormData?: FormData,
  event?: EventInterface,
  fieldState?: FieldState[]
) => {
  if (!localFormData && !fieldState && !event) {
    return initialiseFieldState(conf);
  }

  if (localFormData && !fieldState && !event) {
    return getFieldState(conf, localFormData);
  }

  if (!localFormData && fieldState && event) {
    return updateFieldState(fieldState, event);
  }

  if (localFormData && fieldState && event) {
    return updateFieldState(fieldState, event);
  }

  return;
};

export default simple;
