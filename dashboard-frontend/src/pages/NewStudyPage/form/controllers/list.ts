import { Config, FieldState } from '../../../../types/form';
import {
  Event,
  initialiseGlobalState,
  updateLocalState,
} from '../../../../helpers/state';
import { createNameFor } from '../../../../helpers/strings';
import { translateConfig } from '../../../../helpers/translateConfig';

const list = (config: Config, state?: FieldState[], event?: Event) => {
  const type: string = 'configList';

  const defaultConfig = config.selector?.options[0];

  const getConfig = (baseConfig: Config, dynamicConfig: any) => {
    return dynamicConfig && translateConfig(baseConfig, dynamicConfig);
  };

  if (config.selector && config.type === type) {
    if (!state) {
      const globalState = initialiseGlobalState(
        getConfig(config, defaultConfig)
      );
      return globalState;
    }

    if (state && event) {
      if (event.name === config.selector.name) {
        const index: number = config.selector.options.findIndex(
          (option: Config) => createNameFor(option.title) === event.value
        );

        const selectedConfig: Config = config.selector.options[index];

        const globalState = initialiseGlobalState(
          getConfig(config, selectedConfig)
        );

        return globalState && updateLocalState(globalState, event);
      }

      if (event.type === 'click') {
        return [];
      }

      return updateLocalState(state, event);
    }
  }
};

export default list;

// const i = event.fieldSet

// const updatedDestination = {...state.destinations[i], ...createInitialState(config.selectorOptions[event.value])}

// state.destinations[i] = updatedDestination
// return state
