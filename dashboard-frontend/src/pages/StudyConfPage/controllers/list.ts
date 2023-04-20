import {
  getFieldState,
  initialiseFieldState,
  updateFieldState,
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
  fieldState?: FieldState[]
) => {
  const translatedConf = translateListConf(conf);

  if (!localFormData && !fieldState && !event) {
    const fieldset = initialiseFieldState(translatedConf);

    const translatedButton = translateField(conf.button);

    return [[...fieldset], [translatedButton]];
  }

  if (localFormData && !fieldState && !event) {
    const translatedButton = translateField(conf.button);

    const fieldset = localFormData.map(d => getFieldState(translatedConf, d));

    return [...fieldset, [translatedButton]];
  }

  if (!localFormData && fieldState && event) {
    const fieldset = fieldState.map(s =>
      updateFieldState(s, event, translatedConf)
    );

    const index = fieldset.findIndex((s: any) =>
      s.map((f: FieldState) => f.type === 'button')
    );
    const button = fieldset[index];

    return reorderArray(fieldset, button);
  }

  if (localFormData && fieldState && event) {
    return updateFieldState(fieldState, event, translatedConf);
  }

  return;
};

export default list;
