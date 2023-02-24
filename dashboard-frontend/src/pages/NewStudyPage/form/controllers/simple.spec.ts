import { createMockState, Seed } from '../../../../helpers/mockState';
import { general } from '../configs/general';
import simple from './simple';
import {
  initialiseGlobalState,
  updateLocalState,
} from '../../../../helpers/state';

describe('simple controller', () => {
  let seeds: any[] = [
    { name: 'foo', type: 'text', helper_text: 'foo!' },
    { name: 'bar', type: 'select' },
    { name: 'baz', type: 'list' },
  ];

  it('given a config it creates an initial state when no state is defined', () => {
    const config = general;

    const expectation = initialiseGlobalState(general);

    const res = simple(config);
    expect(res).toStrictEqual(expectation);
  });

  // it('given some local state and an event it updates the value of the target field', () => {
  //   const config = general;
  //   const state = createMockState(seeds);
  //   const event = { name: 'foo', value: 'baz' };

  //   const initialValue = state[0].value;

  //   const expectation = updateLocalState(state, event);
  //   const res = simple(config, state, event);

  //   const updatedValue = res && res[0].value;

  //   expect(res).toStrictEqual(expectation);
  //   expect(updatedValue).toStrictEqual('baz');
  //   expect(updatedValue).not.toEqual(initialValue);
  // });

  // it('only updates the target field and not the values of any other fields', () => {
  //   const config = general;
  //   const state = createMockState(seeds);
  //   const event = { name: 'foo', value: 'baz' };

  //   const initialValue = state[1].value;
  //   expect(initialValue).toEqual('');

  //   const res = simple(config, state, event);

  //   const updatedValue = res && res[1].value;
  //   expect(updatedValue).toEqual('baz');

  //   const initialValue2 = state[2].value;
  //   expect(initialValue2).toEqual([]);

  //   const updatedValue2 = res && res[2].value;
  //   expect(updatedValue2).toEqual(initialValue2);
  // });
});
