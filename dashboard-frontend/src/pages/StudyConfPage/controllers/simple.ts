import {
  initialiseFieldState,
  updateFieldState,
  getFieldState,
} from '../../../helpers/state';
import { ConfObjectBase, FieldState } from '../../../types/conf';
import { EventInterface, FormData } from '../../../types/form';

const simple = (
  conf: ConfObjectBase,
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
    return updateFieldState(fieldState, event, conf);
  }

  if (localFormData && fieldState && event) {
    return updateFieldState(fieldState, event, conf);
  }

  return;
};

export default simple;
