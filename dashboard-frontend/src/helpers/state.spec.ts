import { recruitment_simple } from '../pages/NewStudyPage/form/configs/recruitment/recruitment_simple';
import { recruitment } from '../pages/NewStudyPage/form/configs/recruitment/recruitment';
import { targeting } from '../pages/NewStudyPage/form/configs/targeting';
import Select from '../pages/NewStudyPage/form/inputs/Select';
import Text from '../pages/NewStudyPage/form/inputs/Text';
import { Seed, createMockState } from './mockState';
import { initialiseGlobalState, updateLocalState } from './state';
import { translateConfig } from './translateConfig';

describe('initialiseGlobalState', () => {
  it('given a config of any type it returns a global state when no state is defined', () => {
    const configObject = targeting;

    const configObjectExpectation = [
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
        value: '',
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

    const configObjectResult = initialiseGlobalState(configObject);
    expect(configObjectResult).toStrictEqual(configObjectExpectation);

    const configSelect = translateConfig(recruitment, recruitment_simple);

    const configSelectExpectation = [
      {
        id: 'recruitment_type',
        name: 'recruitment_type',
        type: 'select',
        component: Select,
        label: 'Select a recruitment type',
        helper_text: undefined,
        call_to_action: undefined,
        options: [
          {
            name: 'recruitment_simple',
            label: 'Recruitment simple',
          },
          {
            name: 'recruitment_pipeline',
            label: 'Recruitment pipeline',
          },
          {
            name: 'recruitment_destination',
            label: 'Recruitment destination',
          },
        ],
        value: 'recruitment_simple',
      },
      {
        id: 'ad_campaign_name',
        name: 'ad_campaign_name',
        type: 'text',
        component: Text,
        label: 'Ad campaign name',
        helper_text: 'E.g vlab-vaping-pilot-2',
        call_to_action: undefined,
        options: undefined,
        value: '',
      },
      {
        id: 'budget',
        name: 'budget',
        type: 'number',
        component: Text,
        label: 'Budget',
        helper_text: 'E.g 8400',
        call_to_action: undefined,
        options: undefined,
        value: 0,
      },
      {
        id: 'max_sample',
        name: 'max_sample',
        type: 'number',
        component: Text,
        label: 'Maximum sample',
        helper_text: 'E.g 1000',
        call_to_action: undefined,
        options: undefined,
        value: 0,
      },
      {
        id: 'start_date',
        name: 'start_date',
        type: 'text',
        component: Text,
        label: 'Start date',
        helper_text: 'E.g 2022-01-10',
        call_to_action: undefined,
        options: undefined,
        value: '',
      },
      {
        id: 'end_date',
        name: 'end_date',
        type: 'text',
        component: Text,
        label: 'End date',
        helper_text: 'E.g 2022-01-31',
        call_to_action: undefined,
        options: undefined,
        value: '',
      },
    ];

    const configSelectResult = initialiseGlobalState(configSelect);
    expect(configSelectResult).toStrictEqual(configSelectExpectation);
  });
});

describe('updateLocalState', () => {
  it('given a config of any type, a global state and an event, it can update the local state of a given field', () => {
    const configObject = targeting;
    let state = initialiseGlobalState(configObject);
    let event = { name: 'template_campaign_name', value: 'foo' };

    const expectationConfigObject = {
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
    };

    const resConfigObject = state && updateLocalState(state, event);
    let newValue =
      resConfigObject &&
      resConfigObject[resConfigObject.findIndex(obj => obj.name === event.name)]
        .value;
    expect(newValue).toStrictEqual(expectationConfigObject.value);

    const configSelect = translateConfig(recruitment, recruitment_simple);
    state = initialiseGlobalState(configSelect);
    event = { name: 'ad_campaign_name', value: 'baz' };

    const expectationConfigSelect = {
      id: 'ad_campaign_name',
      name: 'ad_campaign_name',
      type: 'text',
      component: Text,
      label: 'Template campaign name',
      helper_text: 'E.g vlab-vaping-pilot-2',
      call_to_action: undefined,
      options: undefined,
      value: 'baz',
    };

    const resConfigSelect = state && updateLocalState(state, event);
    newValue =
      resConfigSelect &&
      resConfigSelect[resConfigSelect.findIndex(obj => obj.name === event.name)]
        .value;
    expect(newValue).toStrictEqual(expectationConfigSelect.value);
  });
});
