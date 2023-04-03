import {
  initialiseFieldState,
  updateFieldState,
  Event,
  getFieldState,
} from '../../../helpers/state';
import { Conf } from '../../../types/conf';
import { ConfBase, FieldState } from '../../../types/form';

const simple = (
  conf: ConfBase,
  localFormData?: Conf,
  event?: Event,
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
