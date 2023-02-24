import select from './select';
import { recruitment } from '../configs/recruitment/recruitment';
import { initialiseGlobalState } from '../../../../helpers/state';
import { recruitment_simple } from '../configs/recruitment/recruitment_simple';
import { recruitment_pipeline } from '../configs/recruitment/recruitment_pipeline';
import { translateConfig } from '../../../../helpers/translateConfig';
import Select from '../inputs/Select';
import Text from '../inputs/Text';

describe('select controller', () => {
  const base = recruitment;

  it('given a config it creates an initial global state when no state is defined', () => {
    const config = translateConfig(base, recruitment_simple);
    const expectation = initialiseGlobalState(config);

    const res = select(recruitment);

    expect(res).toStrictEqual(expectation);
  });

  it('given some local state and an event it creates a global state with a set of fields', () => {
    const selectedConfig = recruitment_simple;
    const config = translateConfig(base, selectedConfig);
    const state = initialiseGlobalState(config);
    const event = {
      name: 'recruitment_type',
      value: 'recruitment_simple',
    };

    const res = select(recruitment, state, event);

    const staticExpectation = {
      id: 'recruitment_type',
      name: 'recruitment_type',
      type: 'select',
      component: Select,
      label: 'Select a recruitment type',
      helper_text: undefined,
      call_to_action: undefined,
      options: [
        { name: 'recruitment_simple', label: 'Recruitment simple' },
        { name: 'recruitment_pipeline', label: 'Recruitment pipeline' },
        {
          name: 'recruitment_destination',
          label: 'Recruitment destination',
        },
      ],
      value: 'recruitment_simple',
    };

    expect(res && res[0]).toStrictEqual(staticExpectation);

    const dynamicExpectation = res?.slice(1); // returns only the dynamic fields

    const configProps = selectedConfig.fields.map(f => {
      return [f.name, f.type, f.label, f.helper_text];
    });
    const stateProps = dynamicExpectation?.map(e => {
      return [e.name, e.type, e.label, e.helper_text];
    });

    expect(configProps).toStrictEqual(stateProps);
  });

  it('given some local state and an event it can update the global state with a new set of fields', () => {
    let selectedConfig = recruitment_simple;
    let config = translateConfig(base, selectedConfig);
    let state = initialiseGlobalState(config);
    let res = select(recruitment);
    const prevFields = res?.slice(1);

    selectedConfig = recruitment_pipeline;
    config = translateConfig(base, selectedConfig);
    state = initialiseGlobalState(config);
    const event = {
      name: 'recruitment_type',
      value: 'recruitment_pipeline',
    };

    res = select(recruitment, state, event);

    const staticExpectation = {
      id: 'recruitment_type',
      name: 'recruitment_type',
      type: 'select',
      component: Select,
      label: 'Select a recruitment type',
      helper_text: undefined,
      call_to_action: undefined,
      options: [
        { name: 'recruitment_simple', label: 'Recruitment simple' },
        { name: 'recruitment_pipeline', label: 'Recruitment pipeline' },
        {
          name: 'recruitment_destination',
          label: 'Recruitment destination',
        },
      ],
      value: 'recruitment_pipeline',
    };

    expect(res && res[0]).toStrictEqual(staticExpectation);

    const dynamicExpectation = res?.slice(1);
    expect(dynamicExpectation).not.toEqual(prevFields);
  });

  it('given some local state and an event it can update the value of the target field', () => {
    const selectedConfig = recruitment_simple;
    const config = translateConfig(base, selectedConfig);
    const state = initialiseGlobalState(config);
    const event = { name: 'ad_campaign_name', value: 'foo' };
    const previousValue =
      state?.[state.findIndex(f => f.name === event.name)].value;

    const res = select(recruitment, state, event);

    const targetField = res && res[res.findIndex(f => f.name === event.name)];

    const expectation = {
      id: 'ad_campaign_name',
      name: 'ad_campaign_name',
      type: 'text',
      component: Text,
      label: 'Ad campaign name',
      helper_text: 'E.g vlab-vaping-pilot-2',
      call_to_action: undefined,
      options: undefined,
      value: 'foo',
    };

    expect(targetField).toStrictEqual(expectation);
    expect(expectation.value).toStrictEqual(event.value);
    expect(previousValue).not.toEqual(expectation.value);
  });

  it('given multiple events it can update more than one field within the same global state', () => {
    const selectedConfig = recruitment_simple;
    const config = translateConfig(base, selectedConfig);
    const state = initialiseGlobalState(config);
    const event = { name: 'ad_campaign_name', value: 'foo' };

    const res = select(recruitment, state, event);

    const targetField = res && res[res.findIndex(f => f.name === event.name)];

    const expectation = {
      id: 'ad_campaign_name',
      name: 'ad_campaign_name',
      type: 'text',
      component: Text,
      label: 'Ad campaign name',
      helper_text: 'E.g vlab-vaping-pilot-2',
      call_to_action: undefined,
      options: undefined,
      value: 'foo',
    };

    expect(targetField).toStrictEqual(expectation);
    expect(expectation.value).toStrictEqual(event.value);

    const event2 = { name: 'max_sample', value: '12345' };

    const res2 = select(recruitment, state, event2);

    const targetField2 = res && res[res.findIndex(f => f.name === event2.name)];

    const expectation2 = {
      id: 'max_sample',
      name: 'max_sample',
      type: 'number',
      component: Text,
      label: 'Maximum sample',
      helper_text: 'E.g 1000',
      call_to_action: undefined,
      options: undefined,
      value: '12345',
    };

    expect(targetField2).toStrictEqual(expectation2);
    expect(expectation2.value).toStrictEqual(event2.value);

    const values = [expectation.value, expectation2.value];

    const check = values.every(v => res2?.map(f => f.value).includes(v));

    expect(check).toBe(true);

    const insertFakeValue = [expectation.value, expectation2.value, 'baz'];

    const check2 = insertFakeValue.every(v =>
      res2?.map(f => f.value).includes(v)
    );

    expect(check2).toBe(false);
  });
});
