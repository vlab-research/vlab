import { curious_learning } from '../pages/NewStudyPage/form/configs/destinations/curious_learning';
import destinations from '../pages/NewStudyPage/form/configs/destinations/destinations';
import { fly_messenger } from '../pages/NewStudyPage/form/configs/destinations/fly_messenger';
import { typeform } from '../pages/NewStudyPage/form/configs/destinations/typeform';
import { recruitment } from '../pages/NewStudyPage/form/configs/recruitment/recruitment';
import { recruitment_destination } from '../pages/NewStudyPage/form/configs/recruitment/recruitment_destination';
import { recruitment_pipeline } from '../pages/NewStudyPage/form/configs/recruitment/recruitment_pipeline';
import { recruitment_simple } from '../pages/NewStudyPage/form/configs/recruitment/recruitment_simple';
import { translateConfig } from './translateConfig';

describe('translateConfig', () => {
  it('given a config of type select the translator returns a single config with a single set of fields', () => {
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

  it('given a config of type list the translator returns a single config with a single set of fields', () => {
    const baseConfig = destinations;
    const selectedConfig = fly_messenger;

    const expectation = {
      type: 'configList',
      title: 'Destinations',
      description:
        'Every study needs a destination, where do the recruitment ads send the users?',
      fields: [
        {
          name: 'destination',
          type: 'select',
          label: 'Create a destination',
          options: [fly_messenger, typeform, curious_learning],
        },
        {
          name: 'initial_shortcode',
          type: 'text',
          label: 'Initial shortcode',
          helper_text: 'E.g 12345',
        },
        {
          name: 'survey_name',
          type: 'text',
          label: 'Survey Name',
          helper_text: 'Eg. Fly',
        },
        {
          name: 'destination_name',
          type: 'text',
          label: 'Give your destination a name',
          helper_text: 'E.g example-fly-1',
        },
        {
          name: 'add_destination',
          type: 'button',
          label: 'Add destination',
        },
      ],
    };

    const res = translateConfig(baseConfig, selectedConfig);

    expect(res).toStrictEqual(expectation);
  });
});
