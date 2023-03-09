import {
  initialiseGlobalState,
  updateLocalState,
  Event,
} from '../../../../helpers/state';
import { Config, FieldState } from '../../../../types/form';

const simple = (config: Config, state?: FieldState[], event?: Event) => {
  const type: string = 'configObject';

  if (config.type === type) {
    if (!state) {
      return initialiseGlobalState([config]);
    }

    if (state && event) {
      return updateLocalState(state, event);
    }

    return;
  }
};

export default simple;
