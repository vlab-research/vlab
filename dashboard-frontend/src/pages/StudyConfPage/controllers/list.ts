import {
  getFieldState,
  initialiseFieldState,
  updateFieldState,
  updateGlobalState,
} from '../../../helpers/state';
import { EventInterface, FormData } from '../../../types/form';
import { ConfListBase } from '../../../types/conf';
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
    const getButton = (arr: any[]) => {
      const index = arr.findIndex(f => f.type === 'button');
      return arr[index];
    };

    const button = getButton(fieldState);

    if (event.type === 'click' && conf) {
      const updatedFieldState = updateGlobalState(fieldState, translatedConf);

      const button = getButton(updatedFieldState);

      return reorderArray(updatedFieldState, button);
    }

    updateFieldState(fieldState, event);

    return reorderArray(fieldState, button);
  }

  if (localFormData && fieldState && event) {
    return updateFieldState(fieldState, event);
  }

  return;
};

export default list;
