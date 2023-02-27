import { Config, FieldState } from '../../../../types/form';
import {
  Event,
  initialiseGlobalState,
  updateLocalState,
} from '../../../../helpers/state';
import { createNameFor } from '../../../../helpers/strings';
import { translateConfig } from '../../../../helpers/translateConfig';

const recruitment = (config: Config, state?: FieldState[], event?: Event) => {
  const type: string = 'configSelect';

  const defaultConfig = config.selector?.options[0];

  const getConfig = (baseConfig: Config, dynamicConfig: any) => {
    return dynamicConfig && translateConfig(baseConfig, dynamicConfig);
  };

  if (config.selector && config.type === type) {
    if (!state) {
      return initialiseGlobalState(getConfig(config, defaultConfig));
    }

    if (state && event) {
      if (event.name === config.selector.name) {
        const index: number = config.selector.options.findIndex(
          (option: Config) => createNameFor(option.title) === event?.value
        );

        const selectedConfig: Config = config.selector.options[index];

        const globalState = initialiseGlobalState(
          getConfig(config, selectedConfig)
        );

        return globalState && updateLocalState(globalState, event);
      }

      return updateLocalState(state, event);
    }
  }
};

export default recruitment;
