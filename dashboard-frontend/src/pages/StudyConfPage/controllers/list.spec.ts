import list from './list';
import simpleList from '../confs/simpleList';
import initialState from '../../../../mocks/state/initialState';

describe('list controller', () => {
  it('given a list conf it returns some initial fields when no state is defined', () => {
    const expectation = initialState[0].simple_list;
  });
});
