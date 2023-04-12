import {
  ConfBase,
  ConfSelectBase,
  EventInterface,
  FieldState,
} from '../../../types/form';
import { translateConf } from '../../../helpers/translateConf';
import {
  getFieldState,
  initialiseFieldState,
  updateFieldState,
} from '../../../helpers/state';
import { createNameFor } from '../../../helpers/strings';
import { Conf } from '../../../types/conf';
import { getSelectedConf } from '../../../helpers/getSelectedConf';

const recruitment = (
  conf: ConfSelectBase,
  localFormData?: Conf,
  event?: EventInterface,
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

    return updateFieldState(fieldState, event);
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

export default recruitment;
