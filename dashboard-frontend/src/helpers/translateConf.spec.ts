import { mergeConfs, translateListConf } from './translateConf';
import recruitment from '../pages/StudyConfPage/confs/recruitment/base';
import simple from '../pages/StudyConfPage/confs/recruitment/simple';
import translatedConf from '../../mocks/confs/translatedSelectConf';
import simpleList from '../pages/StudyConfPage/confs/simpleList';

describe('mergeConfs', () => {
  it('given two confs it translates them into one', () => {
    const baseConf = recruitment;
    const dynamicConf = simple;

    const expectation = translatedConf;

    const res = mergeConfs(baseConf, dynamicConf);

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
        },
      ],
    };

    const res = translateListConf(conf);

    expect(res).toStrictEqual(expectation);
  });
});
