import select from './select';
import { recruitment } from '../configs/recruitment/recruitment';
import { initialiseGlobalState } from '../../../../helpers/state';
import { recruitment_simple } from '../configs/recruitment/recruitment_simple';
import { recruitment_pipeline } from '../configs/recruitment/recruitment_pipeline';
import { translateConfig } from '../../../../helpers/translateConfig';
import Select from '../inputs/Select';
import Text from '../inputs/Text';
import { getField } from '../../../../helpers/getField';
import { Field } from '../../../../types/form';

describe('select controller', () => {
  const base = recruitment;

  it('given a config of type select the controller can create some initial state when no global state is defined', () => {
    const config = translateConfig(base, recruitment_simple);
    const expectation = initialiseGlobalState(config);

    const res = select(recruitment);

    expect(res).toStrictEqual(expectation);
  });

  it('given an event and some change to the global state the controller can update the global state with a new set of fields', () => {
    const prevConfig = translateConfig(base, recruitment_simple);
    const prevState = initialiseGlobalState(prevConfig);
    const prevRes = select(recruitment);
    const prevFieldset = prevRes && prevRes[0];
    const prevFields = prevFieldset?.slice(1);

    const config = translateConfig(base, recruitment_pipeline);
    const state = initialiseGlobalState(config);
    const event = {
      name: 'recruitment_type',
      type: 'change',
      value: 'recruitment_pipeline',
    };

    const res = select(recruitment, state, event);
    const fieldset = res && res[0];
    const baseField = fieldset[0];

    const baseExpectation = {
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

    const staticFieldPropsFromChosenConfig = recruitment_pipeline.fields.map(
      f => {
        return [f.name, f.type, f.label, f.helper_text];
      }
    );

    const fields = fieldset.slice(1); // returns only the dynamic fields

    const dynamicStateProps = fields?.map((f: Field) => {
      return [f.name, f.type, f.label, f.helper_text];
    });

    expect(state).not.toEqual(prevState);
    expect(fields).not.toEqual(prevFields);
    expect(prevFields).toHaveLength(5);
    expect(fields).toHaveLength(8);
    expect(baseField).toStrictEqual(baseExpectation);
    expect(dynamicStateProps).toStrictEqual(staticFieldPropsFromChosenConfig);
    expect(event.name).toStrictEqual(baseExpectation.name);
    expect(event.value).toStrictEqual(baseExpectation.value);
    expect(baseExpectation.options.some(obj => obj.name === event.value)).toBe(
      true
    );
  });

  it('also works when the event occurs on the default config', () => {
    const config = translateConfig(base, recruitment_simple);
    const state = initialiseGlobalState(config);
    const event = {
      name: 'recruitment_type',
      type: 'change',
      value: 'recruitment_simple',
    };

    const res = select(recruitment, state, event);

    const fieldset = res && res[0];
    const baseField = fieldset[0];

    const baseExpectation = {
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

    expect(baseField).toStrictEqual(baseExpectation);

    const staticFieldPropsFromChosenConfig = recruitment_simple.fields.map(
      f => {
        return [f.name, f.type, f.label, f.helper_text];
      }
    );

    const fields = fieldset.slice(1); // returns only the dynamic fields

    const dynamicStateProps = fields?.map((f: Field) => {
      return [f.name, f.type, f.label, f.helper_text];
    });

    expect(fields).toHaveLength(5);
    expect(baseField).toStrictEqual(baseExpectation);
    expect(dynamicStateProps).toStrictEqual(staticFieldPropsFromChosenConfig);
    expect(event.name).toStrictEqual(baseExpectation.name);
    expect(event.value).toStrictEqual(baseExpectation.value);
    expect(baseExpectation.options.some(obj => obj.name === event.value)).toBe(
      true
    );
  });

  it('given an event and some change to the local state the controller can update the value of the target field', () => {
    const config = translateConfig(base, recruitment_simple);
    const state = initialiseGlobalState(config);
    const event = { name: 'ad_campaign_name', type: 'change', value: 'foo' };
    const prevValue = getField(state, event).value;

    const res = select(recruitment, state, event);

    const targetField = getField(state, event);

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

    const newValue = res && getField(res, event).value;

    expect(targetField).toStrictEqual(expectation);
    expect(expectation.value).toStrictEqual(event.value);
    expect(prevValue).not.toEqual(expectation.value);
    expect(newValue).toEqual(expectation.value);
    expect(newValue).toEqual('foo');
  });

  it('given multiple events the controller can update the values of more than one field within the same global state', () => {
    const config = translateConfig(base, recruitment_simple);
    const state = initialiseGlobalState(config);
    const event = { name: 'ad_campaign_name', type: 'change', value: 'foo' };

    const res = select(recruitment, state, event);

    const targetField = res && getField(res, event);

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

    const event2 = { name: 'max_sample', type: 'change', value: '12345' };

    const res2 = select(recruitment, state, event2);

    const fieldset = res2 && res2[0];

    const targetField2 = res2 && getField(res2, event2);

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

    const values = [expectation.value, expectation2.value];

    // checks to see that both values exist after both events
    const check = values.every(v =>
      fieldset.map((f: any) => f.value).includes(v)
    );

    const insertFakeValue = [expectation.value, expectation2.value, 'baz'];

    const check2 = insertFakeValue.every(v =>
      fieldset.map((f: any) => f.value).includes(v)
    );

    expect(targetField).toStrictEqual(expectation);
    expect(expectation.value).toStrictEqual(event.value);
    expect(targetField2).toStrictEqual(expectation2);
    expect(expectation2.value).toStrictEqual(event2.value);
    expect(check).toBe(true);
    expect(check2).toBe(false);
  });
});
