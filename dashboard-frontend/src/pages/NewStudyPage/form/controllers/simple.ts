import { updateLocalState, Event } from '../../../../helpers/updateLocalState';
import { ConfigBase, FieldState } from '../../../../types/form';

const simple = (config: ConfigBase, state: FieldState[], event: Event) => {
  return updateLocalState(state, event);
};

export default simple;
