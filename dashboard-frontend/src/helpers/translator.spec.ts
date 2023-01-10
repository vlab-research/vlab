import { jsonTranslator, translator } from './translator';
import { recruitment } from '../pages/NewStudyPage/configs/recruitment/recruitment';
import destinations from '../pages/NewStudyPage/configs/destinations/destinations';
import countries from '../fixtures/countries.json';

describe('translator', () => {
  it('takes a configObject and based on its type returns the same config', () => {
    const configObject = {
      type: 'configObject',
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

  it('takes a config-select and returns a new config in the format required for a form builder', () => {
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
            { name: 'recruitment_simple', label: 'Recruitment simple' },
            { name: 'recruitment_pipeline', label: 'Recruitment pipeline' },
            {
              name: 'recruitment_destination',
              label: 'Recruitment destination',
            },
          ],
        },
      ],
    };

    const res = translator(recruitment);
    expect(res).toStrictEqual(expectation);
  });

  it('takes a config-multi and returns a new config in the format required for a form builder', () => {
    const expectation = {
      type: 'config-multi',
      title: 'Destinations',
      description:
        'Every study needs a destination, where do the recruitment ads send the users?',
      fields: [
        {
          name: 'destinations',
          type: 'list',
          label: 'Add new destination',
          options: [
            { name: 'fly_messenger', label: 'Fly Messenger' },
            { name: 'typeform', label: 'Typeform' },
            { name: 'curious_learning', label: 'Curious Learning' },
          ],
        },
      ],
    };

    const res = translator(destinations);
    expect(res).toStrictEqual(expectation);
  });
});

describe('jsonTranslator', () => {
  it('takes a json object and returns an object configured for a form', () => {
    const json = countries;

    const expectation = ['name', 'label'];
    const res = json.map(obj => jsonTranslator(obj));

    const testCase = Object.keys(res[1]);
    expect(testCase).toStrictEqual(expectation);
  });
});
