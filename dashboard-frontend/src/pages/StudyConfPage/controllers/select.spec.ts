import { getField } from '../../../helpers/getField';
import recruitment from '../../StudyConfPage/confs/recruitment/base';
import initialState from '../../../../mocks/state/initialState';
import existingState from '../../../../mocks/state/existingState';
import formData from '../../../../mocks/formData/formData';
import select from './select';

describe('select controller', () => {
  it('given a select conf it returns some initial fields when no state is defined', () => {
    const conf = recruitment;

    const expectation = initialState[0].recruitment;

    const res = select(conf);

    expect(res).toStrictEqual(expectation);
  });

  it('given a select conf and some form data it returns a set of fields with their existing state', () => {
    const conf = recruitment;

    const localFormData = formData['recruitment'];

    const res = select(conf, localFormData);

    const expectation = existingState[0]['recruitment'];

    expect(res).toEqual(expectation);
  });

  it('given a select conf some form data and an event, it updates the value of the field on which the event occurred', () => {
    const conf = recruitment;

    const localFormData = formData['recruitment'];

    const state = existingState[0].recruitment;

    const event = {
      name: `ad_campaign_name`,
      value: 'foo',
      type: 'change',
      fieldType: 'text',
    };

    const newValue = event.value;
    const prevValue = formData['recruitment']['ad_campaign_name'];

    const res = select(conf, localFormData, event, state);

    const targetField = res && getField(res, event);

    expect(targetField?.value).toStrictEqual(newValue);
    expect(targetField?.value).not.toEqual(prevValue);
    expect(targetField?.value).toStrictEqual('foo');
  });
});
