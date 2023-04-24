import { translateConf } from './translateConf';
import { recruitment } from '../pages/StudyConfPage/configs/recruitment/base';
import { simple } from '../pages/StudyConfPage/configs/recruitment/simple';
import translatedConf from '../../mocks/translatedConf';

describe('translateConf', () => {
  it('given two confs it translates them into one', () => {
    const baseConf = recruitment;
    const dynamicConf = simple;

    const expectation = translatedConf;

    const res = translateConf(baseConf, dynamicConf);

    expect(res).toStrictEqual(expectation);
  });
});
