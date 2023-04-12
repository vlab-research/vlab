import {
  initialiseFieldState,
  updateFieldState,
  getFieldState,
} from '../../../helpers/state';
import {
  FieldState,
  ConfObjectBase,
  EventInterface,
} from '../../../types/form';
import { Conf } from '../../../types/conf';

const list = (
  conf: ConfObjectBase,
  localFormData?: Conf,
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

export default list;
