import { mergeConfs, translateListConf } from './translateConf';
import recruitment from '../pages/StudyConfPage/confs/recruitment/base';
import simple from '../pages/StudyConfPage/confs/recruitment/simple';
import translatedConf from '../../mocks/confs/translatedSelectConf';
import simpleList from '../pages/StudyConfPage/confs/simpleList';
import destinations from '../pages/StudyConfPage/confs/destinations/base';
import messenger from '../pages/StudyConfPage/confs/destinations/messenger';
import app from '../pages/StudyConfPage/confs/destinations/app';
import web from '../pages/StudyConfPage/confs/destinations/web';

describe('mergeConfs', () => {
  it('given two confs it translates them into one', () => {
    const baseConf = recruitment;
    const selectedConf = simple;

    const expectation = translatedConf;

    const res = mergeConfs(baseConf, selectedConf);

    expect(res).toStrictEqual(expectation);
  });

  it('works when the base conf is nested within another', () => {
    const baseConf = destinations.input.conf;
    const selectedConf = messenger;

    const expectation = {
      type: 'confSelect',
      title: 'Destinations',
      description:
        'Every study needs a destination, where do the recruitment ads send the users?',
      fields: [
        {
          name: 'destination_type',
          type: 'select',
          label: 'Select a destination type',
          options: [messenger, web, app],
        },
        {
          name: 'initial_shortcode',
          type: 'text',
          label: 'Initial shortcode',
          helper_text: 'E.g 12345',
        },
        {
          name: 'destination_name',
          type: 'text',
          label: 'Destination name',
          helper_text: 'E.g example-fly-1',
        },
      ],
    };

    const res = mergeConfs(baseConf, selectedConf);

    expect(res).toStrictEqual(expectation);
  });
});

describe('translateListConf', () => {
  it('given a conf of type list it returns a simple conf with a set of fields', () => {
    const conf = simpleList;

    const expectation = {
      type: 'confList',
      title: 'Simple List',
      description: 'simple list conf...',
      key: 'foo',
      button: { name: 'add_button', type: 'button' },
      fields: [
        {
          name: 'foo',
          type: 'text',
          label: 'I am a list item',
          helper_text: 'Foo',
          options: undefined,
          conf: null,
        },
      ],
    };
    const res = translateListConf(conf);

    expect(res).toStrictEqual(expectation);
  });

  it('works for more complex lists with nested confs', () => {
    const conf = destinations;

    const selectedConf = messenger;

    const expectation = {
      type: 'confList',
      title: 'Destinations',
      description: '',
      key: 'destination_create',
      button: { name: 'add_button', type: 'button' },
      fields: [
        {
          name: 'destination_create',
          type: 'fieldset',
          label: 'Create a destination',
          helper_text: undefined,
          options: undefined,
          conf: {
            type: 'confSelect',
            title: 'Destinations',
            description:
              'Every study needs a destination, where do the recruitment ads send the users?',
            fields: [
              {
                name: 'destination_type',
                type: 'select',
                label: 'Select a destination type',
                options: [messenger, web, app],
              },
              {
                name: 'initial_shortcode',
                type: 'text',
                label: 'Initial shortcode',
                helper_text: 'E.g 12345',
              },
              {
                name: 'destination_name',
                type: 'text',
                label: 'Destination name',
                helper_text: 'E.g example-fly-1',
              },
            ],
          },
        },
      ],
    };

    const res = translateListConf(conf, selectedConf);

    expect(res).toStrictEqual(expectation);
  });
});
