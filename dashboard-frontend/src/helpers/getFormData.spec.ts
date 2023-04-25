import { getFormData } from './getFormData';
import initialState from '../../mocks/state/initialState';
import formData from '../../mocks/formData/formData';
import general from '../pages/StudyConfPage/confs/general';
import simpleList from '../pages/StudyConfPage/confs/simpleList';

import existingState from '../../mocks/state/existingState';

describe('getFormData', () => {
  it('given a conf and some fieldstate it returns form data as a single object', () => {
    const conf = general;
    const fieldState = existingState[0]['general'];

    const expectation = formData['general'];

    const res = getFormData(conf, fieldState);

    expect(res).toStrictEqual(expectation);
  });

  it('also returns form data as an array if it derives from a list', () => {
    const conf = simpleList;
    const fieldState = existingState[0]['simple_list'];

    const expectation = formData['simple_list'];

    const res = getFormData(conf, fieldState);

    expect(res).toStrictEqual(expectation);
  });
});
