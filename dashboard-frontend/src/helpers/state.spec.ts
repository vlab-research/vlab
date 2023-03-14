import Select from '../pages/NewStudyPage/form/components/inputs/Select';
import Text from '../pages/NewStudyPage/form/components/inputs/Text';
import { targeting } from '../pages/NewStudyPage/form/configs/targeting';
import { getField } from './getField';
import { initialiseGlobalState, updateLocalState } from './state';

describe('initialiseGlobalState', () => {
  it('given a config of type object it returns a global state when no state is defined', () => {
    const configObject = targeting;

    const expectation = [
      {
        id: 'template_campaign_name',
        name: 'template_campaign_name',
        type: 'text',
        component: Text,
        label: 'Template campaign name',
        helper_text:
          'If you have created template ads to target certain variables, this is the name of the campaign that has those ads.',
        options: undefined,
        value: '',
      },
      {
        id: 'distribution_vars',
        name: 'distribution_vars',
        type: 'select',
        component: Select,
        label: 'Distribution variables',
        helper_text: undefined,
        options: [
          { name: 'default', label: 'Select a distribution variable' },
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

    const res = initialiseGlobalState(configObject);

    expect(res).toStrictEqual(expectation);
  });

  describe('updateLocalState', () => {
    it('given a config of type object it can update the value of a given field when the user generates some input', () => {
      const configObject = targeting;
      const state = initialiseGlobalState(configObject);
      const event = {
        name: 'template_campaign_name',
        value: 'foobar',
        type: 'change',
      };

      const expectation = {
        id: 'template_campaign_name',
        name: 'template_campaign_name',
        type: 'text',
        component: Text,
        label: 'Template campaign name',
        helper_text:
          'If you have created template ads to target certain variables, this is the name of the campaign that has those ads.',
        options: undefined,
        value: event.value,
      };

      const res = state && updateLocalState(state, event);

      const newValue = getField(res, event).value;
      expect(newValue).toStrictEqual(expectation.value);
      expect(newValue).toStrictEqual(event.value);
      expect(newValue).toStrictEqual('foobar');
      expect(newValue).not.toEqual('');
    });
  });
});
