import initialState from '../../../../mocks/initialState';
import { recruitment } from '../configs/recruitment/base';
import select from './select';
import formData from '../../../../mocks/formData';
import existingState from '../../../../mocks/existingState';
import { getField } from '../../../helpers/getField';

describe('select controller', () => {
  it('given a recruitment conf it returns some initial fields when no state is defined', () => {
    const expectation = initialState[0].recruitment;

    const res = select(recruitment);

    expect(res).toStrictEqual(expectation);
  });

  it('given a recruitment conf and some form data it returns a set of fields with their existing state', () => {
    const conf = recruitment;

    const localFormData = formData['recruitment'];

    const res = select(conf, localFormData);

    const expectation = existingState[0]['recruitment'];

    expect(res).toEqual(expectation);
  });

  it('given a recruitment conf, some form data and an event it updates the value of the field on which the event occurred', () => {
    const conf = recruitment;

    const localFormData = formData['recruitment'];

    const state = existingState[0].recruitment;

    const event = {
      name: `ad_campaign_name`,
      value: 'foo',
      type: 'change',
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
