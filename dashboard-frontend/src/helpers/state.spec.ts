import { getFieldState, initialiseFieldState, updateFieldState } from './state';
import { getField } from './getField';
import { general } from '../pages/StudyConfPage/configs/general';
import { create_study } from '../pages/NewStudyPage/configs/create_study';
import state from '../../mocks/state';
import formData from '../../mocks/formData';

describe('initialiseFieldState', () => {
  it('given a conf it returns some initial field state when no state is defined', () => {
    const conf = create_study;

    const expectation = state[0]['create_study'];

    const res = initialiseFieldState(conf);

    expect(res).toStrictEqual(expectation);
  });

  it('works for a study conf too', () => {
    const conf = general;

    const expectation = state[0]['general'];

    const res = initialiseFieldState(conf);

    expect(res).toStrictEqual(expectation);
  });
});

describe('getFieldState', () => {
  it('given a conf and some local form data it returns some initial field state with the field values set to the given form values', () => {
    const conf = general;
    const localFormData = formData['general'];

    const expectedValues = Object.values(localFormData);

    const res = getFieldState(conf, localFormData);

    const resValues = Object.values(res.map(f => f.value));

    expect(resValues).toEqual(expectedValues);
  });
});

describe('updateFieldState', () => {
  it('given some field state and an event it can update the target field with the value from that event', () => {
    const fieldState = state[0]['general'];

    const event = {
      name: 'instagram_id',
      value: 'baz',
      type: 'change',
    };

    const res = updateFieldState(fieldState, event);

    const updatedField = getField(res, event);

    expect(updatedField.value).toEqual('baz');
    expect(updatedField.value).not.toEqual('baz!');
    expect(updatedField.value).toEqual(event.value);
  });

  it('works when the event occurrs on a select component', () => {
    const fieldState = state[0]['general'];

    const event = {
      name: 'objective',
      value: 'link_clicks',
      type: 'change',
    };

    const res = updateFieldState(fieldState, event);

    const updatedField = getField(res, event);

    expect(updatedField.value).toEqual('link_clicks');
    expect(updatedField.value).not.toEqual('link_clicks!');
    expect(updatedField.value).toEqual(event.value);
  });
});
