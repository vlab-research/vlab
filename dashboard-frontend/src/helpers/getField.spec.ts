import Text from './../pages/NewStudyPage/components/form/inputs/Text';
import { getField } from './getField';
import initialState from '../../mocks/state/initialState';

describe('getField', () => {
  it('given some fields and an event it returns the field on which the event occurred', () => {
    const fieldState = initialState[0]['general'];

    const event = {
      name: 'instagram_id-6',
      value: 'foo',
      type: 'change',
      fieldType: 'text',
    };

    const expectation = {
      id: 'instagram_id',
      name: 'instagram_id',
      type: 'text',
      component: Text,
      label: 'Instagram Id',
      helper_text: 'E.g 2327764173962588',
      options: undefined,
      value: '',
      conf: null,
    };

    const res = getField(fieldState, event);

    expect(res).toStrictEqual(expectation);
  });
});
