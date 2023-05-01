import { initialiseFieldState } from '../../../helpers/state';
import { general } from '../configs/general';
import { getField } from '../../../helpers/getField';
import { create_study } from '../../NewStudyPage/confs/create_study';
import initialState from '../../../../mocks/initialState';
import Text from '../../NewStudyPage/components/form/inputs/Text';
import { translateField } from '../../../helpers/translateField';
import formData from '../../../../mocks/formData';
import simple from './simple';

describe('simple controller', () => {
  it('given a conf it returns some initial fields when no state is defined', () => {
    const confs = [create_study, general];

    const expectation = confs.map(conf => initialiseFieldState(conf));

    const res = confs.map(conf => simple(conf));

    expect(res).toStrictEqual(expectation);
  });

  it('given a conf and some form data it returns a set of fields with their existing state', () => {
    const conf = create_study;

    const localFormData = formData['create_study'];

    const res = simple(conf, localFormData);

    const expectation = [
      {
        id: 'name',
        name: 'name',
        type: 'text',
        component: Text,
        label: 'Give your study a name',
        helper_text: 'E.g example-fly-conf',
        options: undefined,
        value: 'foo',
      },
    ];

    expect(res).toEqual(expectation);
  });

  it('works for study confs too', () => {
    const conf = general;

    const localFormData = formData['general'];

    const res = simple(conf, localFormData);

    const expectation = conf.fields.map(f => translateField(f, localFormData));

    expect(res).toEqual(expectation);
  });

  it('given some existing form data and an event it updates the state of the field on which the event occurred', () => {
    const conf = create_study;

    const localFormData = formData['create_study'];

    const event = {
      name: 'name',
      value: 'baz',
      type: 'change',
    };

    const fieldState = initialState[0].create_study;

    const newValue = event.value;
    const prevValue = 'foo';

    const res = simple(conf, localFormData, event, fieldState);

    const targetField = res && getField(res, event);
    expect(targetField?.value).toStrictEqual(newValue);
    expect(targetField?.value).toStrictEqual(event.value);
    expect(targetField?.value).toStrictEqual('baz');
    expect(targetField?.value).not.toEqual(prevValue);
  });

  it('works for updating study confs too', () => {
    const conf = general;

    const localFormData = formData['general'];

    const state = initialState[0].general;

    const event = {
      name: `instagram_id`,
      value: 'baz',
      type: 'change',
    };

    const newValue = event.value;
    const prevValue = formData['general']['instagram_id'];

    const res = simple(conf, localFormData, event, state);

    const targetField = res && getField(res, event);
    expect(targetField?.value).toStrictEqual(newValue);
    expect(targetField?.value).not.toEqual(prevValue);
    expect(targetField?.value).toStrictEqual('baz');
  });
});
