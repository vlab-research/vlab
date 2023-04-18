import { getSelectedConf } from './getSelectedConf';
import recruitment from '../pages/StudyConfPage/confs/recruitment/base';
import pipeline_experiment from '../pages/StudyConfPage/confs/recruitment/pipeline_experiment';
import simple from '../pages/StudyConfPage/confs/recruitment/simple';
import destination from '../pages/StudyConfPage/confs/recruitment/destination';

describe('getSelectedConf', () => {
  it('given a recruitment conf and some form data it returns the nested conf from which the form data derives', () => {
    const localFormData = {
      end_date: '2022-07-27T00:00:00',
      start_date: '2022-07-26T00:00:00',
      max_sample: 'iron-overload-men',
      budget: 10000,
      ad_campaign_name: 'test-123',
    };

    const expectation = simple;

    const res = getSelectedConf(recruitment, localFormData);

    expect(res).toStrictEqual(expectation);
  });

  it('works with a different set of form data', () => {
    const localFormData = {
      end_date: '2022-07-27T00:00:00',
      start_date: '2022-07-26T00:00:00',
      arms: 2,
      recruitment_days: 10,
      offset_days: 20,
      ad_campaign_name_base: 'iron-overload-men',
      budget_per_arm: 10000,
      max_sample_per_arm: 100,
    };

    const expectation = pipeline_experiment;

    const res = getSelectedConf(recruitment, localFormData);

    expect(res).toStrictEqual(expectation);
  });

  it('works with form data that is made up of fields shared across multiple recruitment types', () => {
    const localFormData = {
      end_date: '2022-07-27T00:00:00',
      start_date: '2022-07-26T00:00:00',
      ad_campaign_name_base: 'iron-overload-men',
      budget_per_arm: 10000,
      max_sample_per_arm: 100,
    };

    const expectation = destination;

    const res = getSelectedConf(recruitment, localFormData);

    expect(res).toStrictEqual(expectation);
  });
});
