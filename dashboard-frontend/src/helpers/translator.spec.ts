import { translator } from './translator';
import { recruitment } from '../pages/NewStudyPage/configs/recruitment/recruitment';
import { recruitment_simple } from '../pages/NewStudyPage/configs/recruitment/recruitment_simple';
import { recruitment_destination_experiment } from '../pages/NewStudyPage/configs/recruitment/recruitment_destination_experiment';
import { recruitment_pipeline_experiment } from '../pages/NewStudyPage/configs/recruitment/recruitment_pipeline_experiment';
import destinations from '../pages/NewStudyPage/configs/destinations/destinations';
import { fly_messenger_destination } from '../pages/NewStudyPage/configs/destinations/fly_messenger_destination';
import { typeform } from '../pages/NewStudyPage/configs/destinations/typeform';
import { curious_learning } from '../pages/NewStudyPage/configs/destinations/curious_learning';

describe('translator', () => {
  it('takes a config-object and based on its type returns the same config', () => {
    const configObject = {
      type: 'config-object',
      title: 'foo',
      description: 'foobaz',
      fields: [
        {
          name: 'bazzle',
          type: 'select',
          label: 'select an option',
          options: [
            {
              name: 'foo',
              label: 'Foo',
            },
            {
              name: 'bar',
              label: 'Bar',
            },
            {
              name: 'baz',
              label: 'Baz',
            },
          ],
        },
      ],
    };

    const expectation = configObject;

    const res = translator(configObject);
    expect(res).toStrictEqual(expectation);
  });

  it('takes a config-select or config-multi and returns a new config in the format required for a form builder', () => {
    const expectation = {
      type: 'config-select',
      title: 'Recruitment',
      description:
        'The "recruitment" configuration describes how/where recruitment will take place. Every study needs to recruit from somewhere.',
      fields: [
        {
          name: 'recruitment',
          type: 'select',
          label: 'Select a recruitment type',
          options: [
            recruitment_simple,
            recruitment_pipeline_experiment,
            recruitment_destination_experiment,
          ],
        },
      ],
    };

    const res = translator(recruitment);
    expect(res).toStrictEqual(expectation);
  });

  const expectation2 = {
    type: 'config-multi',
    title: 'Destinations',
    description:
      'Every study needs a destination, where do the recruitment ads send the users?',
    fields: [
      {
        name: 'destinations',
        type: 'list',
        label: 'Add new destination',
        options: [fly_messenger_destination, typeform, curious_learning],
      },
    ],
  };

  const res = translator(destinations);
  expect(res).toStrictEqual(expectation2);
});
