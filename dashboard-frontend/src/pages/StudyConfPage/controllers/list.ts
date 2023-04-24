import {
  getFieldState,
  initialiseFieldState,
  updateFieldState,
  updateGlobalState,
} from '../../../helpers/state';
import { EventInterface, FormData } from '../../../types/form';
import { ConfListBase, FieldState } from '../../../types/conf';
import { translateListConf } from '../../../helpers/translateConf';
import { translateField } from '../../../helpers/translateField';
import { reorderArray } from '../../../helpers/arrays';

const list = (
  conf: ConfListBase,
  localFormData?: FormData[],
  event?: EventInterface,
  fieldState?: any[]
) => {
  const translatedConf = translateListConf(conf);

  const getButton = (arr: any[]) => {
    const index = arr.findIndex(f => f.type === 'button');
    return arr[index];
  };

  const translateFieldState = (state: FieldState[]) => {
    const button = getButton(state);

    const updatedFieldState = updateGlobalState(state, translatedConf);

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
    if (event.type === 'click' && conf) {
      return translateFieldState(fieldState);
    }

    updateFieldState(fieldState, event);

    const button = getButton(fieldState);

    return reorderArray(fieldState, button);
  }

  if (localFormData && fieldState && event) {
    if (event.type === 'click' && conf) {
      return translateFieldState(fieldState);
    }
    updateFieldState(fieldState, event);

    const button = getButton(fieldState);

    return reorderArray(fieldState, button);
  }

  return;
};

export default list;
