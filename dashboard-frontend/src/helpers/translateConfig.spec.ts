import { recruitment } from '../pages/NewStudyPage/form/configs/recruitment/recruitment';
import { recruitment_destination } from '../pages/NewStudyPage/form/configs/recruitment/recruitment_destination';
import { recruitment_pipeline } from '../pages/NewStudyPage/form/configs/recruitment/recruitment_pipeline';
import { recruitment_simple } from '../pages/NewStudyPage/form/configs/recruitment/recruitment_simple';
import { translateConfig } from './translateConfig';

describe('translateConfig', () => {
  it('given two configs it returns a single config with single set of fields', () => {
    const baseConfig = recruitment;
    const selectedConfig = recruitment_simple;

    const expectation = {
      type: 'configSelect',
      title: 'Recruitment',
      description:
        'The "recruitment" configuration describes how/where recruitment will take place. Every study needs to recruit from somewhere.',
      fields: [
        {
          name: 'recruitment_type',
          type: 'select',
          label: 'Select a recruitment type',
          options: [
            recruitment_simple,
            recruitment_pipeline,
            recruitment_destination,
          ],
        },
        {
          name: 'ad_campaign_name',
          type: 'text',
          label: 'Ad campaign name',
          helper_text: 'E.g vlab-vaping-pilot-2',
        },
        {
          name: 'budget',
          type: 'number',
          label: 'Budget',
          helper_text: 'E.g 8400',
        },
        {
          name: 'max_sample',
          type: 'number',
          label: 'Maximum sample',
          helper_text: 'E.g 1000',
        },
        {
          name: 'start_date',
          type: 'text',
          label: 'Start date',
          helper_text: 'E.g 2022-01-10',
        },
        {
          name: 'end_date',
          type: 'text',
          label: 'End date',
          helper_text: 'E.g 2022-01-31',
        },
      ],
    };

    const res = translateConfig(baseConfig, selectedConfig);

    expect(res).toStrictEqual(expectation);
  });
});
