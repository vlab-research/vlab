import { getField } from './getField';
import { initialiseFieldState } from './state';
import Text from './../pages/NewStudyPage/components/form/inputs/Text';
import { general } from '../pages/StudyConfPage/configs/general';

describe('getField', () => {
  it('given some fields and an event it returns the field on which the event occurred', () => {
    const conf = general;
    const fields = initialiseFieldState(conf);
    const event = {
      name: 'instagram_id',
      value: 'foo',
      type: 'change',
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
    };

    const res = getField(fields, event);

    expect(res).toStrictEqual(expectation);
  });
});
