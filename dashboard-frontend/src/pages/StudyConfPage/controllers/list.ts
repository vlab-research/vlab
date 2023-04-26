import {
  getFieldState,
  initialiseFieldState,
  updateFieldState,
  updateGlobalState,
} from '../../../helpers/state';
import { EventInterface, FormData } from '../../../types/form';
import { ConfList, FieldState } from '../../../types/conf';
import { translateListConf } from '../../../helpers/translateConf';
import { translateField } from '../../../helpers/translateField';
import { reorderArray } from '../../../helpers/arrays';

const list = (
  conf: ConfList,
  localFormData?: FormData[],
  event?: EventInterface,
  fieldState?: any[]
) => {
  const defaultConf = conf.input.conf?.selector?.options[0];

  const translatedConf = translateListConf(conf, defaultConf);

  const getButton = (arr: any[]) => {
    const index = arr.findIndex(f => f.type === 'button');
    return arr[index];
  };

  const button = fieldState && getButton(fieldState);

  const translateFieldState = (fieldState: FieldState[]) => {
    const updatedFieldState = updateGlobalState(fieldState, translatedConf);
    return reorderArray(updatedFieldState, button);
  };

  if (!localFormData && !fieldState && !event) {
    const inputs = initialiseFieldState(translatedConf);

    const translatedButton = translateField(conf.button);

    return [...inputs, translatedButton];
  }

  if (localFormData && !fieldState && !event) {
    const inputs = localFormData
      .map(d => getFieldState(translatedConf, d))
      .flat(1);

    const translatedButton = translateField(conf.button);

    return [...inputs, translatedButton];
  }

  if (!localFormData && fieldState && event) {
    if (event.type === 'click') {
      return translateFieldState(fieldState);
    }

    updateFieldState(fieldState, event);

    return reorderArray(fieldState, button);
  }

  if (localFormData && fieldState && event) {
    if (event.type === 'click') {
      return translateFieldState(fieldState);
    }
    updateFieldState(fieldState, event);

    return reorderArray(fieldState, button);
  }

  return;
};

export default list;
