import { EventInterface } from '../../../types/form';
import { translateConf } from '../../../helpers/translateConf';
import {
  getFieldState,
  initialiseFieldState,
  updateFieldState,
} from '../../../helpers/state';
import { createNameFor } from '../../../helpers/strings';
import { getSelectedConf } from '../../../helpers/getSelectedConf';
import { ConfSelectBase, FieldState, ConfBase } from '../../../types/conf';

const select = (
  conf: ConfSelectBase,
  localFormData?: FormData,
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

      return (
        globalState && updateFieldState(translatedConf, globalState, event)
      );
    }

    return updateFieldState(conf, fieldState, event);
  }

  if (localFormData && fieldState && event) {
    if (event.name === conf.selector.name) {
      const index: number = conf.selector.options.findIndex(
        (option: ConfBase) => createNameFor(option.title) === event.value
      );

      const selectedConf: ConfBase = conf.selector.options[index];

      const translatedConf = getConf(conf, selectedConf);

      const globalState = initialiseFieldState(translatedConf);

      return (
        globalState && updateFieldState(translatedConf, globalState, event)
      );
    }

    return updateFieldState(conf, fieldState, event);
  }
};

export default select;
