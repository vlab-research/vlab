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

  const updateLocalStateWithoutGlobalEvent = (state: FieldState[]) => {
    const clone = [...state];
    clone[0].value = defaultConfig && createNameFor(defaultConfig.title);
    return clone;
  };

  if (config.selector && config.type === type) {
    if (!state) {
      const newConfig = getConfig(config, defaultConfig);
      return initialiseGlobalState(newConfig);
    }

    if (state) {
      if (event) {
        if (event.name === config.selector.name) {
          const index: number = config.selector.options.findIndex(
            (option: Config) => createNameFor(option.title) === event?.value
          );

          const selectedConfig: Config = config.selector.options[index];

          const globalState = initialiseGlobalState(
            getConfig(config, selectedConfig)
          );

          globalState && updateLocalState(globalState, event);

          return globalState;
        }

        return updateLocalState(state, event);
      }

      const newConfig = getConfig(config, defaultConfig);

      const globalState = initialiseGlobalState(newConfig);

      globalState && updateLocalStateWithoutGlobalEvent(globalState);

      return globalState;
    }
  }
};

export default recruitment;
