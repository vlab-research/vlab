import { initialiseFieldState, updateFieldState } from '../../../helpers/state';
import { EventInterface } from '../../../types/form';
import { ConfObjectBase, FieldState } from '../../../types/conf';
import select from './select';

const list = (
  conf: ConfObjectBase,
  localFormData?: FormData[],
  event?: EventInterface,
  fieldState?: FieldState[]
) => {
  const nestedConf = conf.fields.filter(f => f.conf)[0].conf;

  if (!localFormData && !fieldState && !event) {
    return initialiseFieldState(conf);
  }

  if (localFormData && !fieldState && !event) {
    return localFormData.map(d => select(nestedConf, d));
  }

  if (!localFormData && fieldState && event) {
    return updateFieldState(conf, fieldState, event);
  }

  if (localFormData && fieldState && event) {
    return updateFieldState(conf, fieldState, event);
  }

  return;
};

export default list;
