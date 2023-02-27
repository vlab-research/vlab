import { recruitment } from '../pages/NewStudyPage/form/configs/recruitment/recruitment';
import { recruitment_simple } from '../pages/NewStudyPage/form/configs/recruitment/recruitment_simple';
import { targeting } from '../pages/NewStudyPage/form/configs/targeting';
import { getFieldIndex } from './getFieldIndex';
import { initialiseGlobalState } from './state';
import { translateConfig } from './translateConfig';

describe('getFieldIndex', () => {
  it('maps over some state and returns a field based on a given event', () => {
    let config = targeting;
    let state = initialiseGlobalState(config);
    let event = { name: 'template_campaign_name', value: 'foo' };

    let expectation = 0;

    let res = state && getFieldIndex(state, event);

    expect(res).toStrictEqual(expectation);

    config = translateConfig(recruitment, recruitment_simple);
    state = initialiseGlobalState(config);
    event = { name: 'ad_campaign_name', value: 'baz' };

    expectation = 1;

    res = state && getFieldIndex(state, event);

    expect(res).toStrictEqual(expectation);
  });
});
