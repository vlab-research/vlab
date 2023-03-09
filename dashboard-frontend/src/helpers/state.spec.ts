import { recruitment_simple } from '../pages/NewStudyPage/form/configs/recruitment/recruitment_simple';
import { recruitment } from '../pages/NewStudyPage/form/configs/recruitment/recruitment';
import { targeting } from '../pages/NewStudyPage/form/configs/targeting';
import Select from '../pages/NewStudyPage/form/inputs/Select';
import Text from '../pages/NewStudyPage/form/inputs/Text';
import { initialiseGlobalState, updateLocalState } from './state';
import { translateConfig } from './translateConfig';
import destinations from '../pages/NewStudyPage/form/configs/destinations/destinations';
import { fly_messenger } from '../pages/NewStudyPage/form/configs/destinations/fly_messenger';
import Button from '../pages/NewStudyPage/form/buttons/Button';

describe('initialiseGlobalState', () => {
  it('given a config of type object it returns a global state when no state is defined', () => {
    const configObject = targeting;
    const configs = [configObject];

    const expectation = [
      [
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
      ],
    ];

    const res = initialiseGlobalState(configs);
    expect(res).toStrictEqual(expectation);
  });

  it('given a config of type select it returns a global state when no state is defined', () => {
    const configSelect = translateConfig(recruitment, recruitment_simple);
    const configs = [configSelect];

    const expectation = [
      [
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
      ],
    ];

    const res = initialiseGlobalState(configs);
    expect(res).toStrictEqual(expectation);
    expect(res).toHaveLength(1);
  });
});

it('given a config of type list it returns a global state when no state is defined', () => {
  const configList = translateConfig(destinations, fly_messenger);
  const configs = [configList];

  const expectation = [
    [
      {
        id: 'destination',
        name: 'destination',
        type: 'select',
        component: Select,
        label: 'Create a destination',
        helper_text: undefined,
        call_to_action: undefined,
        options: [
          {
            label: 'Fly Messenger',
            name: 'fly_messenger',
          },
          {
            label: 'Typeform',
            name: 'typeform',
          },
          {
            label: 'Curious Learning',
            name: 'curious_learning',
          },
        ],
        value: 'fly_messenger',
      },
      {
        id: 'initial_shortcode',
        name: 'initial_shortcode',
        type: 'text',
        component: Text,
        label: 'Initial shortcode',
        helper_text: 'E.g 12345',
        call_to_action: undefined,
        options: undefined,
        value: '',
      },
      {
        id: 'survey_name',
        name: 'survey_name',
        type: 'text',
        component: Text,
        label: 'Survey Name',
        helper_text: 'Eg. Fly',
        call_to_action: undefined,
        options: undefined,
        value: '',
      },
      {
        id: 'destination_name',
        name: 'destination_name',
        type: 'text',
        component: Text,
        label: 'Give your destination a name',
        helper_text: 'E.g example-fly-1',
        call_to_action: undefined,
        options: undefined,
        value: '',
      },
      {
        id: 'add_destination',
        name: 'add_destination',
        type: 'button',
        component: Button,
        label: 'Add destination',
        helper_text: undefined,
        call_to_action: undefined,
        options: undefined,
        value: '',
      },
    ],
  ];

  const res = initialiseGlobalState(configs);
  expect(res).toStrictEqual(expectation);
  expect(res).toHaveLength(1);
});

describe('updateLocalState', () => {
  it('given a config of type object it can update the value of a given field when the user generates some input', () => {
    const configObject = targeting;
    const configs = [configObject];
    const state = initialiseGlobalState(configs);
    const event = {
      name: 'template_campaign_name',
      value: 'foo',
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
      call_to_action: undefined,
      options: undefined,
      value: 'foo',
    };

    const resConfigObject = state && updateLocalState(state, event);
    const newValue =
      resConfigObject &&
      resConfigObject[resConfigObject.findIndex(obj => obj.name === event.name)]
        .value;
    expect(newValue).toStrictEqual(expectation.value);
  });

  // it('given a config of type select it can update the value of a given field when the user generates some input', () => {
  //   const configSelect = translateConfig(recruitment, recruitment_simple);
  //   const state = initialiseGlobalState(configSelect);
  //   const event = { name: 'ad_campaign_name', value: 'baz', type: 'change' };

  //   const expectationConfigSelect = {
  //     id: 'ad_campaign_name',
  //     name: 'ad_campaign_name',
  //     type: 'text',
  //     component: Text,
  //     label: 'Template campaign name',
  //     helper_text: 'E.g vlab-vaping-pilot-2',
  //     call_to_action: undefined,
  //     options: undefined,
  //     value: 'baz',
  //   };

  //   const resConfigSelect = state && updateLocalState(state, event);
  //   const newValue =
  //     resConfigSelect &&
  //     resConfigSelect[resConfigSelect.findIndex(obj => obj.name === event.name)]
  //       .value;
  //   expect(newValue).toStrictEqual(expectationConfigSelect.value);
  // });

  // it('given a config of type list it can update the value of a given field when the user generates some input', () => {
  //   const configList = translateConfig(destinations, fly_messenger);
  //   const state = initialiseGlobalState(configList);
  //   const event = { name: 'ad_campaign_name', value: 'baz', type: 'change' };

  //   const expectationConfigList = {
  //     id: 'initial_shortcode',
  //     name: 'initial_shortcode',
  //     type: 'text',
  //     component: Text,
  //     label: 'Initial shortcode',
  //     helper_text: 'E.g 12345',
  //     call_to_action: undefined,
  //     options: undefined,
  //     value: 'foobar',
  //   };

  //   const resConfigSelect = state && updateLocalState(state, event);
  //   const newValue =
  //     resConfigSelect &&
  //     resConfigSelect[resConfigSelect.findIndex(obj => obj.name === event.name)]
  //       .value;
  //   expect(newValue).toStrictEqual(expectationConfigList.value);
  // });
});
