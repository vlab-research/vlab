import { targeting } from '../pages/NewStudyPage/form/configs/targeting';
import { getField } from './getField';
import { initialiseGlobalState } from './state';
import Text from './../pages/NewStudyPage/form/components/inputs/Text';

describe('getField', () => {
  it('given some global state and an event it returns the field on which the event ocurred', () => {
    const config = targeting;
    const state = initialiseGlobalState(config);
    const event = {
      name: 'template_campaign_name',
      value: 'foo',
      type: 'change',
    };

    const expectation = {
      id: 'template_campaign_name',
      name: 'template_campaign_name',
      type: 'text',
      component: Text,
      label: 'Template campaign name',
      helper_text:
        'If you have created template ads to target certain variables, this is the name of the campaign that has those ads.',
      options: undefined,
      value: '',
    };

    const res = state && getField(state, event);

    expect(res).toStrictEqual(expectation);
  });
});
