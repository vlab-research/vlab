import { general } from '../configs/general';
import simple from './simple';
import { initialiseGlobalState } from '../../../../helpers/state';
import { targeting } from '../configs/targeting';
import Select from '../inputs/Select';
import Text from '../inputs/Text';

describe('simple controller', () => {
  it('given a config it creates an initial state when no state is defined', () => {
    const config = general;

    const expectation = initialiseGlobalState(general);

    const res = simple(config);
    expect(res).toStrictEqual(expectation);
  });

  it('given some local state and an event it updates the value of the target field', () => {
    let config = targeting;
    let state = initialiseGlobalState(config);
    const event = { name: 'template_campaign_name', value: 'foo' };

    const initialValue =
      state && state[state.findIndex(obj => obj.name === event.name)].value;

    const expectation = [
      {
        id: 'template_campaign_name',
        name: 'template_campaign_name',
        type: 'text',
        component: Text,
        label: 'Template campaign name',
        helper_text:
          'If you have created template ads to target certain variables, this is the name of the campaign that has those ads.',
        call_to_action: undefined,
        options: undefined,
        value: 'foo',
      },
      {
        id: 'distribution_vars',
        name: 'distribution_vars',
        type: 'select',
        component: Select,
        label: 'Distribution variables',
        helper_text: undefined,
        call_to_action: undefined,
        options: [
          {
            name: 'default',
            label: 'Select a distribution variable',
          },
          {
            name: 'location',
            label: 'Location',
          },
          {
            name: 'gender',
            label: 'Gender',
          },
          {
            name: 'age',
            label: 'Age',
          },
        ],
        value: 'default',
      },
    ];

    const res = simple(config, state, event);

    const updatedValue =
      res && res[res.findIndex(obj => obj.name === event.name)].value;

    expect(res).toStrictEqual(expectation);
    expect(updatedValue).toStrictEqual(event.value);
    expect(updatedValue).toStrictEqual('foo');
    expect(updatedValue).not.toEqual(initialValue);
  });
});