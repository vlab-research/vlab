import general from '../pages/StudyConfPage/confs/general';
import simpleList from '../pages/StudyConfPage/confs/simpleList';
import create_study from '../pages/NewStudyPage/confs/create_study';
import { getFieldState, initialiseFieldState, updateFieldState } from './state';
import { getField } from './getField';
import initialState from '../../mocks/state/initialState';
import formData from '../../mocks/formData/formData';
import translatedConf from '../../mocks/confs/translatedConf';

describe('initialiseFieldState', () => {
  it('given a simple conf it returns some initial field state when no state is defined', () => {
    const conf = create_study;

    const expectation = initialState[0]['create_study'];

    const res = initialiseFieldState(conf);

    expect(res).toStrictEqual(expectation);
  });

  it('works for a simple study conf', () => {
    const conf = general;

    const expectation = initialState[0]['general'];

    const res = initialiseFieldState(conf);

    expect(res).toStrictEqual(expectation);
  });

  it('and a select conf', () => {
    const conf = translatedConf;

    const expectation = initialState[0]['recruitment'];

    const res = initialiseFieldState(conf);

    expect(res).toStrictEqual(expectation);
  });

  it('and a list conf', () => {
    const conf = simpleList;

    const expectation = initialState[0]['simple_list'];

    const res = initialiseFieldState(conf);

    expect(res).toStrictEqual(expectation);
  });
});

describe('getFieldState', () => {
  it('given a simple study conf and some local form data it returns some initial field state and maps any form data to their corresponding to field values', () => {
    const conf = general;
    const localFormData = formData['general'];

    const expectedValues = Object.values(localFormData);

    const res = getFieldState(conf, localFormData);

    const resValues = Object.values(res.map(f => f.value));

    expect(resValues).toEqual(expectedValues);
  });

  it('works for a select conf', () => {
    const conf = translatedConf;
    const localFormData = formData['recruitment'];

    const expectedValues = Object.values(localFormData);

    //   [
    //   'recruitment_simple',
    //   'vlab-most-used-prog-1',
    //   10000,
    //   1000,
    //   '2022-07-26T00:00:00',
    //   '2022-08-05T00:00:00'
    // ]

    const res = getFieldState(conf, localFormData);

    const resValues = Object.values(res.map(f => f.value));

    expect(resValues).toEqual(expectedValues);
  });

  it('works for a list conf', () => {
    const conf = simpleList;
    const localFormData = formData['simple_list'];

    const expectedValues = localFormData.map(d => Object.values(d));

    //   [ [ 'foobar', 'buzz' ], [ 'foobaz' ], [ 'foobazzle' ] ]

    const res = localFormData.map(d => getFieldState(conf, d));

    const fieldState = res.map(r => r.filter(f => f.value));

    const resValues = fieldState.map(s => s.map(f => f.value));

    expect(resValues).toEqual(expectedValues);
  });
});

describe('updateFieldState', () => {
  it('given some field state and a change event it can update the target field with the value from that event', () => {
    const fieldState = initialState[0]['general'];

    const event = {
      name: 'instagram_id',
      value: 'baz',
      type: 'change',
      fieldType: 'text',
    };

    const res = updateFieldState(fieldState, event);

    const updatedField = getField(res, event);

    expect(updatedField.value).toEqual('baz');
    expect(updatedField.value).not.toEqual('baz!');
    expect(updatedField.value).toEqual(event.value);
  });

  it('works when the event occurrs on a select component', () => {
    const fieldState = initialState[0]['general'];

    const event = {
      name: 'objective',
      value: 'link_clicks',
      type: 'change',
      fieldType: 'select',
    };

    const res = updateFieldState(fieldState, event);

    const updatedField = getField(res, event);

    expect(updatedField.value).toEqual('link_clicks');
    expect(updatedField.value).not.toEqual('link_clicks!');
    expect(updatedField.value).toEqual(event.value);
  });

  it('works when the event occurs on a select component with nested confs', () => {
    const fieldState = initialState[0]['recruitment'];

    const event = {
      name: 'recruitment_type',
      value: 'recruitment_pipeline',
      type: 'change',
      fieldType: 'select',
    };

    const res = updateFieldState(fieldState, event);

    const updatedField = getField(res, event);

    expect(updatedField.value).toEqual('recruitment_pipeline');
    expect(updatedField.value).not.toEqual('recruitment_simple');
    expect(updatedField.value).toEqual(event.value);
  });

  it('works for click events when the event occurs on a button', () => {
    const conf = simpleList;
    const fieldState = initialState[0]['simple_list'];

    const event = {
      name: 'add_button',
      value: 'add_button',
      type: 'click',
      fieldType: 'button',
    };

    const fieldStateOnFirstClick = updateFieldState(fieldState, event, conf);

    console.log(fieldStateOnFirstClick);

    // expect(fieldStateOnFirstClick).toHaveLength(2);

    const fieldStateOnSecondClick = updateFieldState(
      fieldStateOnFirstClick,
      event,
      conf
    );

    console.log(fieldStateOnSecondClick);

    // expect(fieldStateOnSecondClick).toHaveLength(3);
  });
});
