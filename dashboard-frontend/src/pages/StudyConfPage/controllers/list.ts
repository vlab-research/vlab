import {
  getFieldState,
  initialiseFieldState,
  updateFieldState,
  Event,
} from '../../../helpers/state';
import { createNameFor } from '../../../helpers/strings';
import { getSelectedConf } from '../../../helpers/getSelectedConf';
import { translateConf } from '../../../helpers/translateConf';
import { Conf } from '../../../types/conf';
import { ConfBase, ConfSelectBase, FieldState } from '../../../types/form';

const list = (
  conf: ConfSelectBase,
  localFormData?: Conf,
  event?: Event,
  fieldState?: FieldState[]
) => {
  const getConf = (baseConf: ConfSelectBase, dynamicConf: any) => {
    return dynamicConf && translateConf(baseConf, dynamicConf);
  };

  if (!localFormData && !fieldState && !event) {
    const defaultConf = conf.selector?.options[0];

    const translatedConf = getConf(conf, defaultConf);

    return initialiseFieldState(translatedConf);
  }

  if (localFormData && !fieldState && !event) {
    const selectedConf: ConfBase = getSelectedConf(conf, localFormData);

    const translatedConf = getConf(conf, selectedConf);

    const translateFormData = (conf: ConfBase) => {
      return {
        recruitment_type: createNameFor(conf.title),
        ...localFormData,
      };
    };

    const translatedFormData = translateFormData(selectedConf);

    return getFieldState(translatedConf, translatedFormData);
  }

  if (!localFormData && fieldState && event) {
    if (event.name === conf.selector.name) {
      const index: number = conf.selector.options.findIndex(
        (option: ConfBase) => createNameFor(option.title) === event?.value
      );

      const selectedConf: ConfBase = conf.selector.options[index];

      const translatedConf = getConf(conf, selectedConf);

      const globalState = initialiseFieldState(translatedConf);

      return globalState && updateFieldState(globalState, event);
    }
  }

  if (localFormData && fieldState && event) {
    if (event.name === conf.selector.name) {
      const index: number = conf.selector.options.findIndex(
        (option: ConfBase) => createNameFor(option.title) === event.value
      );

      const selectedConf: ConfBase = conf.selector.options[index];

      const translatedConf = getConf(conf, selectedConf);

      const globalState = initialiseFieldState(translatedConf);

      return globalState && updateFieldState(globalState, event);
    }

    return updateFieldState(fieldState, event);
  }
};

export default list;
