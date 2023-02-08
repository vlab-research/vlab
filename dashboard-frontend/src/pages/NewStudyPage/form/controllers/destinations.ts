import { ConfigBase, FieldState } from '../../../../types/form';
import { Event } from '../../../../helpers/updateLocalState';

const destinations = (
  config: ConfigBase,
  state: FieldState[],
  event: Event
) => {
  // TODO some funky stuff with state.ctaButton
  // TODO change the ifs  to a switch statement
  // if (event.field === 'ctaButton') {
  //   return {
  //     ...state,
  //     destinations: [
  //       ...state.destinations,
  //       createInitialState(config.destinationFieldSet),
  //     ],
  //   };
  // }
  // if (event.field === 'deleteButton') {
  //   const i = event.fieldSet;
  //   // TODO remove destination i from state.destinations
  // }
  // if (event.field === 'type') {
  //   const i = event.fieldSet;
  //   const updatedDestination = {
  //     ...state.destinations[i],
  //     ...createInitialState(config.selectorOptions[event.value]),
  //   };
  //   state.destinations[i] = updatedDestination;
  //   return state;
  // }
};

export default destinations;
