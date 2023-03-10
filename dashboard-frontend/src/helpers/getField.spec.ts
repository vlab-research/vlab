import { recruitment } from '../pages/NewStudyPage/form/configs/recruitment/recruitment';
import { recruitment_simple } from '../pages/NewStudyPage/form/configs/recruitment/recruitment_simple';
import { targeting } from '../pages/NewStudyPage/form/configs/targeting';
import { getField } from './getField';
import { initialiseGlobalState } from './state';
import { translateConfig } from './translateConfig';
import Text from './../pages/NewStudyPage/form/inputs/Text';

describe('getField', () => {
  it('given some state and an event it returns the target field', () => {
    let config = targeting;
    let state = initialiseGlobalState(config);
    let event = {
      name: 'template_campaign_name',
      value: 'foo',
      type: 'change',
    };

    let expectation = {
      id: 'template_campaign_name',
      name: 'template_campaign_name',
      type: 'text',
      component: Text,
      label: 'Template campaign name',
      helper_text:
        'If you have created template ads to target certain variables, this is the name of the campaign that has those ads.',
      call_to_action: undefined,
      options: undefined,
      value: '',
    };

    let res = state && getField(state, event);

    expect(res).toStrictEqual(expectation);

    config = translateConfig(recruitment, recruitment_simple);
    state = initialiseGlobalState(config);
    event = { name: 'ad_campaign_name', value: 'baz', type: 'change' };

    expectation = {
      id: 'ad_campaign_name',
      name: 'ad_campaign_name',
      type: 'text',
      component: Text,
      label: 'Ad campaign name',
      helper_text: 'E.g vlab-vaping-pilot-2',
      call_to_action: undefined,
      options: undefined,
      value: '',
    };

    res = state && getField(state, event);

    expect(res).toStrictEqual(expectation);
    expect(res.value).toStrictEqual(expectation.value);
    expect(res.value).toStrictEqual('');
  });
});
