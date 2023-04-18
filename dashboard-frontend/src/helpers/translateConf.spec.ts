import { translateConf } from './translateConf';
import recruitment from '../pages/StudyConfPage/confs/recruitment/base';
import simple from '../pages/StudyConfPage/confs/recruitment/simple';
import translatedConf from '../../mocks/confs/translatedConf';

describe('translateConf', () => {
  it('given two confs it translates them into one', () => {
    const baseConf = recruitment;
    const dynamicConf = simple;

    const expectation = translatedConf;

    const res = translateConf(baseConf, dynamicConf);

    expect(res).toStrictEqual(expectation);
  });
});
